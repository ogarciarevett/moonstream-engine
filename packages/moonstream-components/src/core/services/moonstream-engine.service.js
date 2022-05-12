import { http } from "../utils";
const API = process.env.NEXT_PUBLIC_ENGINE_API_URL;

export const getContracts = () => async () => {
  return http({
    method: "GET",
    url: `${API}/drops/contracts`,
  });
};

export const getDropList = (dropperAddress, chainName) => async (address) => {
  return http({
    method: "GET",
    url: `${API}/drops/claims`,
    params: {
      dropper_contract_address: encodeURIComponent(dropperAddress),
      blockchain: chainName,
      claimant_address: address,
    },
  });
};

export const getAdminList =
  (terminusAddress, chainName, poolId, offset, limit) => async () => {
    return http({
      method: "GET",
      url: `${API}/drops/terminus/claims`,
      params: {
        terminus_address: encodeURIComponent(terminusAddress),
        blockchain: chainName,
        terminus_pool_id: poolId,
        offset: offset,
        limit: limit,
      },
    });
  };

export const getClaim = (claimId, address) => {
  return http({
    method: "GET",
    url: `${API}/drops/`,
    params: { address: address, dropper_claim_id: claimId },
  });
};

export const createDropperClaim =
  ({ dropperContractAddress }) =>
  async ({ title, description, deadline, terminusAddress, terminusPoolId }) => {
    const data = new FormData();
    data.append("dropper_contract_address", dropperContractAddress);
    data.append("title", title);
    data.append("description", description);
    data.append("claim_block_deadline", deadline);
    terminusAddress && data.append("terminus_address", terminusAddress);
    terminusPoolId && data.append("terminus_pool_id", terminusPoolId);

    return http({
      method: "POST",
      url: `${API}/drops/claims`,
      data: data,
    });
  };

export const getClaimants =
  ({ dropperClaimId }) =>
  ({ limit, offset }) => {
    return http({
      method: "GET",
      url: `${API}/drops/claimants`,
      params: {
        dropper_claim_id: encodeURIComponent(dropperClaimId),
        offset: encodeURIComponent(offset),
        limit: encodeURIComponent(limit),
      },
    });
  };

export const setClaimants = ({ dropperClaimId, claimants }) => {
  const data = { dropper_claim_id: dropperClaimId, claimants: claimants };

  return http({
    method: "POST",
    url: `${API}/drops/claimants`,
    data: data,
  });
};

export const deleteClaimants =
  ({ dropperClaimId }) =>
  ({ list }) => {
    const data = new FormData();
    data.append("dropper_claim_id", dropperClaimId);
    data.append("addresses", list);

    return http({
      method: "DELETE",
      url: `${API}/drops/claimants`,
      data: { dropper_claim_id: dropperClaimId, addresses: list },
    });
  };

export const getTime = () => async () => {
  return http({
    method: "GET",
    url: `${API}/now`,
  });
};

export const getTerminus = (chainName) => async () => {
  return http({
    method: "GET",
    url: `${API}/drops/terminus`,
    params: { blockchain: chainName },
  });
};

export const deactivate = ({ dropperClaimId }) => {
  return http({
    method: "PUT",
    url: `${API}/drops/claims/${dropperClaimId}/deactivate`,
  });
};

export const activate = ({ dropperClaimId }) => {
  return http({
    method: "PUT",
    url: `${API}/drops/claims/${dropperClaimId}/activate`,
  });
};

export const updateDrop =
  ({ dropperClaimId }) =>
  ({ title, description, deadline }) => {
    return http({
      method: "PUT",
      url: `${API}/drops/claims/${dropperClaimId}`,
      data: {
        title: title,
        description: description,
        claim_block_deadline: deadline,
      },
    });
  };
