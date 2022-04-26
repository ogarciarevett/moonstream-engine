"""
Lootbox API.
"""
import logging
import time
from typing import List, Dict, Optional, Any
from uuid import UUID

from brownie import network, web3


from fastapi import Body, FastAPI, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from . import actions
from . import data
from . import db
from . import Dropper
from . import signatures
from .middleware import DropperHTTPException, DropperAuthMiddleware
from .settings import (
    ENGINE_BROWNIE_NETWORK,
    DOCS_TARGET_PATH,
    ORIGINS,
    ENGINE_DROPPER_ADDRESS,
)

network.connect(ENGINE_BROWNIE_NETWORK)

DROPPER = Dropper.Dropper(ENGINE_DROPPER_ADDRESS)

RESOURCE_TYPE_DROP_WHITELIST = "drop_whitelist"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tags_metadata = [
    {"name": "test", "description": "Test."},
]

app = FastAPI(
    title=f"Lootbox HTTP API",
    description="Lootbox API endpoints.",
    version="v0.0.1",
    openapi_tags=tags_metadata,
    openapi_url="/openapi.json",
    docs_url=None,
    redoc_url=f"/{DOCS_TARGET_PATH}",
)


whitelist_paths: Dict[str, str] = {}
whitelist_paths.update(
    {
        "/ping": "GET",
        "/time": "GET",
        "/drops": "GET",
        "/drops/claims": "GET",
        "/drops/contracts": "GET",
    }
)


app.add_middleware(DropperAuthMiddleware, whitelist=whitelist_paths)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping", response_model=data.PingResponse)
async def ping_handler() -> data.PingResponse:
    """
    Check server status.
    """
    return data.PingResponse(status="ok")


@app.get("/time", response_model=int)
async def time_handler() -> int:
    """
    Get current time.
    """
    return int(time.time())


@app.get("/drops", response_model=data.DropResponse)
async def get_drop_handler(
    dropper_claim_id: UUID,
    address: str,
    db_session: Session = Depends(db.yield_db_session),
) -> data.DropResponse:
    """
    Get signed transaction for user with the given address.
    example:
    curl -X GET "http://localhost:8000/drops?claim_id=<claim_number>&address=<user_address>"
    """

    address = web3.toChecksumAddress(address)

    try:
        claimant = actions.get_claimant(db_session, dropper_claim_id, address)
    except Exception as e:
        raise DropperHTTPException(status_code=500, detail=f"Can't get claimant: {e}")

    message_hash = DROPPER.claim_message_hash(
        claimant.claim_id,
        claimant.address,
        claimant.claim_block_deadline,
        claimant.amount,
    )

    try:
        signature = signatures.DROP_SIGNER.sign_message(message_hash)
    except signatures.AWSDescribeInstancesFail:
        raise DropperHTTPException(status_code=500)
    except signatures.SignWithInstanceFail:
        raise DropperHTTPException(status_code=500)
    except Exception as err:
        logger.error(f"Unexpected error in signing message process: {err}")
        raise DropperHTTPException(status_code=500)
    return data.DropResponse(
        claimant=claimant.address,
        amount=claimant.amount,
        claim_id=claimant.claim_id,
        block_deadline=claimant.claim_block_deadline,
        signature=signature,
    )


@app.get("/drops/contracts")
async def get_dropper_contracts_handler(
    blockchain: Optional[str] = Query(None),
    db_session: Session = Depends(db.yield_db_session),
) -> Any:
    """
    Get list of drops for a given dropper contract.
    """

    try:
        results = actions.list_dropper_contracts(
            db_session=db_session, blockchain=blockchain
        )
    except NoResultFound:
        raise DropperHTTPException(status_code=404, detail="No drops found.")
    except Exception as e:
        logger.error(f"Can't get list of dropper contracts end with error: {e}")
        raise DropperHTTPException(status_code=500, detail="Can't get contracts")

    return results


@app.get("/drops/claims", response_model=data.DropListResponse)
async def get_drop_list_handler(
    dropper_contract_address: str,
    blockchain: str,
    claimant_address: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    limit: int = 10,
    offset: int = 0,
    db_session: Session = Depends(db.yield_db_session),
) -> data.DropListResponse:
    """
    Get list of drops for a given dropper contract and claimant address.
    """

    claimant_address = web3.toChecksumAddress(claimant_address)

    dropper_contract_address = web3.toChecksumAddress(dropper_contract_address)

    try:
        results = actions.get_claims(
            db_session=db_session,
            dropper_contract_address=dropper_contract_address,
            blockchain=blockchain,
            claimant_address=claimant_address,
            active=active,
            limit=limit,
            offset=offset,
        )
    except NoResultFound:
        raise DropperHTTPException(status_code=404, detail="No drops found.")
    except Exception as e:
        logger.error(
            f"Can't get claims for user {claimant_address} end with error: {e}"
        )
        raise DropperHTTPException(status_code=500, detail="Can't get claims")

    return data.DropListResponse(drops=results)


@app.post("/drops/claims", response_model=data.DropCreatedResponse)
async def create_drop(
    register_request: data.DropRegisterRequest = Body(...),
    db_session: Session = Depends(db.yield_db_session),
) -> data.DropCreatedResponse:

    """
    Create a drop for a given dropper contract.
    required: Web3 verification of signature (middleware probably)
    body:
        dropper_contract_address: address of dropper contract
        claim_id: claim id
        address: address of claimant
        amount: amount of drop

    """

    if register_request.terminus_address is None:
        register_request.terminus_address = web3.toChecksumAddress(
            "0x0000000000000000000000000000000000000000"
        )
    else:
        register_request.terminus_address = web3.toChecksumAddress(
            register_request.terminus_address
        )

    if register_request.terminus_pool_id is None:
        register_request.terminus_pool_id = 0

    try:
        claim = actions.create_claim(
            db_session=db_session,
            dropper_contract_id=register_request.dropper_contract_id,
            title=register_request.title,
            description=register_request.description,
            claim_block_deadline=register_request.claim_block_deadline,
            terminus_address=register_request.terminus_address,
            terminus_pool_id=register_request.terminus_pool_id,
            claim_id=register_request.claim_id,
        )
    except NoResultFound:
        raise DropperHTTPException(status_code=404, detail="Dropper contract not found")
    except Exception as e:
        logger.error(f"Can't create claim: {e}")
        raise DropperHTTPException(status_code=500, detail="Can't create claim")

    return data.DropCreatedResponse(
        dropper_claim_id=claim.id,
        dropper_contract_id=claim.dropper_contract_id,
        title=claim.title,
        description=claim.description,
        claim_block_deadline=claim.claim_block_deadline,
        terminus_address=claim.terminus_address,
        terminus_pool_id=claim.terminus_pool_id,
        claim_id=claim.claim_id,
    )


@app.get("/drops/claimants", response_model=data.DropListResponse)
async def get_claimants(
    dropper_claim_id: UUID,
    limit: int = 10,
    offset: int = 0,
    db_session: Session = Depends(db.yield_db_session),
) -> List[str]:
    """
    Get list of claimants for a given dropper contract.

    curl -X GET "http://localhost:8000/drops/claimants?claim_id=<claim_number>"

    """
    try:
        results = actions.get_claimants(
            db_session=db_session,
            dropper_claim_id=dropper_claim_id,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.info(f"Can't add claimants for claim {dropper_claim_id} with error: {e}")
        raise DropperHTTPException(status_code=500, detail=f"Error adding claimants")

    return data.DropListResponse(drops=list(results))


@app.post("/drops/claimants", response_model=data.ClaimantsResponse)
async def create_claimants(
    request: Request,
    add_claimants_request: data.DropAddClaimantsRequest = Body(...),
    db_session: Session = Depends(db.yield_db_session),
) -> data.ClaimantsResponse:

    """
    Add addresses to particular claim

    curl --location --request POST 'localhost:7191/drops/claimants' \
    --header 'Content-Type: application/json' \
    --data-raw '{"dropper_claim_id": UUID, "claimants":[{"address": address, "amount": int}]}'

    """

    added_by = "me"  # request.state.user.address read from header in auth middleware

    try:
        results = actions.add_claimants(
            db_session=db_session,
            dropper_claim_id=add_claimants_request.dropper_claim_id,
            claimants=add_claimants_request.claimants,
            added_by=added_by,
        )
    except Exception as e:
        logger.info(
            f"Can't add claimants for claim {add_claimants_request.dropper_claim_id} with error: {e}"
        )
        raise DropperHTTPException(status_code=500, detail=f"Error adding claimants")

    return data.ClaimantsResponse(claimants=results)


@app.delete("/drops/claimants", response_model=data.RemoveClaimantsResponse)
async def create_claimants(
    request: Request,
    remove_claimants_request: data.DropRemoveClaimantsRequest = Body(...),
    db_session: Session = Depends(db.yield_db_session),
) -> data.RemoveClaimantsResponse:

    """
    Remove addresses to particular claim
    curl --location --request DELETE 'localhost:7191/drops/claimants' \
    --header 'Content-Type: application/json' \
    --data-raw '{"dropper_claim_id": UUID, "claimants":[address]}'
    """

    try:
        results = actions.delete_claimants(
            db_session=db_session,
            dropper_claim_id=remove_claimants_request.dropper_claim_id,
            addresses=remove_claimants_request.addresses,
        )
    except Exception as e:
        logger.info(
            f"Can't remove claimants for claim {remove_claimants_request.dropper_claim_id} with error: {e}"
        )
        raise DropperHTTPException(status_code=500, detail=f"Error removing claimants")

    return data.RemoveClaimantsResponse(addresses=results)
