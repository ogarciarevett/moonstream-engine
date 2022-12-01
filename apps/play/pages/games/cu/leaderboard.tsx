import React, { useState } from "react";
import { useQuery } from "react-query";
import { getLayout } from "moonstream-components/src/layouts/EngineLayout";
import {
  Box,
  Heading,
  Flex,
  Table,
  Thead,
  Tbody,
  Th,
  Tr,
  Td,
  Link,
  Spinner,
  Text,
  Icon,
  IconButton,
  Spacer,
  HStack,
  Image,
} from "@chakra-ui/react";
import http from "moonstream-components/src/core/utils/http";
import queryCacheProps from "moonstream-components/src/core/hooks/hookCommon";
import {
  SHADOWCORN_CONTRACT_ADDRESS,
} from "moonstream-components/src/core/cu/constants";
import { GrNext, GrPrevious } from "react-icons/gr";
import { FiExternalLink } from "react-icons/fi";

const playAssetPath = "https://s3.amazonaws.com/static.simiotics.com/play";
const assets = {
  shadowcornsLogo: `${playAssetPath}/cu/shadowcorns-logo.png`,
};

const buildOpenseaLink = (tokenId: string) => {
  return `https://opensea.io/assets/matic/${SHADOWCORN_CONTRACT_ADDRESS}/${tokenId}`
};

const Leaderboard = () => {

  const [limit, setLimit] = React.useState<number>(25);
  const [offset, setOffset] = React.useState<number>(0);

  const fetchLeaders = async (pageLimit: number, pageOffset: number) => {
    return http(
      {
        method: "GET",
        url: `https://engineapi.moonstream.to/leaderboard/?leaderboard_id=863429ad-ea0d-4cbf-b0f9-6e5c3fc83bb2&limit=${pageLimit}&offset=${pageOffset}`,
      },
      true
    );
  };

  const leaders = useQuery(
    ["fetch_leaders", limit, offset],
    () => {
      return fetchLeaders(limit, offset).then((res) => {
        try {
          // console.log("Offset is ", offset);
          // console.log(res);
          return res;
        } catch (err) {
          console.log(err);
        }
      });
    },
    {
      ...queryCacheProps,
      onSuccess: () => {},
    }
  );

  const panelBackground = "#2D2D2D";

  return (
    <Box
      className="Dashboard"
      borderRadius={"xl"}
      pt={10}
      minH="100vh"
      bgColor="#1A1D22"
    >
      <Flex mb={10} bgColor={panelBackground} rounded="lg" px={10} py={10} direction="column">
        <HStack mb={10}>
          <Image ml={2} alt={"Shadowcorns"} h="50px" src={assets["shadowcornsLogo"]} />
          <Heading>Throwing Shade Leaderboard</Heading>
        </HStack>
        <Flex ml={"10px"} mr={"250px"}>
          <IconButton
            aria-label="Next"
            size="sm"
            colorScheme="whiteAlpha"
            icon={<GrPrevious />}
            disabled={offset < limit}
            onClick={() => {
              if(offset >= limit) {
                setOffset(offset - limit);
              }
            }}
          ></IconButton>
          <Spacer />
          <Text hidden={!leaders.data}>Showing results {offset} - {offset + leaders.data?.data.length}</Text>
          <Spacer />
          <IconButton
            aria-label="Next"
            size="sm"
            colorScheme="whiteAlpha"
            icon={<GrNext />}
            disabled={!leaders.data || leaders.data.data.length < limit}
            onClick={() => {
              setOffset(offset + limit);
            }}  
          ></IconButton>
        </Flex>
        {leaders.data ? (
          <Table variant="unstyled">
            <Thead>
              <Tr>
                <Th><Text fontSize="lg" fontFamily="heading">Rank</Text></Th>
                <Th><Text fontSize="lg" fontFamily="heading">Shadowcorn ID</Text></Th>
                <Th><Text fontSize="lg" fontFamily="heading">Score</Text></Th>
              </Tr>
            </Thead>
                <Tbody>
                  {leaders.data.data.map((item: any, idx: number) => {
                    return (
                      <Tr key={idx}>
                        <Td>{item.rank}</Td>
                        <Td>              
                          <Link
                            mb={2}
                            _hover={{ bgColor: "#454545" }}
                            href={buildOpenseaLink(item.address)}
                            isExternal
                          >
                            {item.address}&nbsp;&nbsp;&nbsp;
                            <Icon as={FiExternalLink} />
                          </Link>
                        </Td>
                        <Td>{item.score}</Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              
          </Table>
        ) : (
          <Spinner alignSelf="center" />
        )}
      </Flex>
    </Box>
  );
};

Leaderboard.getLayout = getLayout;

export default Leaderboard;
