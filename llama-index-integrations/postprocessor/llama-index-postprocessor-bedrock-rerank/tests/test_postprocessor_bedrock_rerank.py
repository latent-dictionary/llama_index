from unittest import TestCase, mock

import boto3
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.postprocessor.bedrock_rerank import BedrockRerank


class TestBedrockRerank(TestCase):
    def test_class(self):
        names_of_base_classes = [b.__name__ for b in BedrockRerank.__mro__]
        self.assertIn(BaseNodePostprocessor.__name__, names_of_base_classes)

    def test_bedrock_rerank(self):
        exp_rerank_response = {
            "results": [
                {
                    "index": 2,
                    "relevanceScore": 0.9,
                },
                {
                    "index": 3,
                    "relevanceScore": 0.8,
                },
            ]
        }

        input_nodes = [
            NodeWithScore(node=TextNode(id_="1", text="first 1")),
            NodeWithScore(node=TextNode(id_="2", text="first 2")),
            NodeWithScore(node=TextNode(id_="3", text="last 1")),
            NodeWithScore(node=TextNode(id_="4", text="last 2")),
        ]

        expected_nodes = [
            NodeWithScore(node=TextNode(id_="3", text="last 1"), score=0.9),
            NodeWithScore(node=TextNode(id_="4", text="last 2"), score=0.8),
        ]

        bedrock_client = boto3.client("bedrock-agent-runtime", region_name="us-west-2")
        reranker = BedrockRerank(client=bedrock_client, top_n=2)

        with mock.patch.object(
            bedrock_client, "rerank", return_value=exp_rerank_response
        ):
            query_bundle = QueryBundle(query_str="last")

            actual_nodes = reranker.postprocess_nodes(
                input_nodes, query_bundle=query_bundle
            )

            self.assertEqual(len(actual_nodes), len(expected_nodes))
            for actual_node_with_score, expected_node_with_score in zip(
                actual_nodes, expected_nodes
            ):
                self.assertEqual(
                    actual_node_with_score.node.get_content(),
                    expected_node_with_score.node.get_content(),
                )
                self.assertAlmostEqual(
                    actual_node_with_score.score, expected_node_with_score.score
                )

    def test_bedrock_rerank_consistent_top_n(self):
        input_nodes = [NodeWithScore(node=TextNode(id_="4", text="last 1"))]

        bedrock_client = boto3.client("bedrock-agent-runtime", region_name="us-west-2")
        reranker = BedrockRerank(client=bedrock_client, top_n=4)
        self.assertEqual(reranker.top_n, 4)

        with mock.patch.object(bedrock_client, "rerank") as patched_rerank:
            reranker.postprocess_nodes(input_nodes, query_str="last")
            self.assertTrue(patched_rerank.called)
            num_results = patched_rerank.call_args.kwargs["rerankingConfiguration"][
                "bedrockRerankingConfiguration"
            ]["numberOfResults"]
            self.assertEqual(num_results, len(input_nodes))
            self.assertEqual(reranker.top_n, 4)
