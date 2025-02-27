#!/usr/bin/env python3

# This module is for tests that validate our tests or test framework, make sure
# tests are running correctly, or test our python test helpers.

import pytest
from validate import (
    check_query_f,
    collapse_order_not_selset,
    validate_http_anyq_with_allowed_responses,
)
from ruamel.yaml.comments import CommentedMap

usefixtures = pytest.mark.usefixtures


@usefixtures('postgis', 'per_class_tests_db_state')
class TestTests1:
    """
    Test various things about our test framework code. Validate that tests work
    as we expect.
    """

    # NOTE: We don't care about this for now, but should adapt this to test
    # that xfail detection in code that handles `--accept` works correctly.
    @pytest.mark.xfail(reason="expected")
    def test_tests_xfail(self, request):
        try:
            marker = request.node.get_closest_marker("xfail")
            print(marker)
            if marker.name != 'xfail':
                print("FAIL!")
                return True  # Force a test failure when xfail strict
        except:
            print("FAIL!")
            return True  # Force a test failure when xfail strict
        assert 0, "Expected failure is expected"

    # Adapted arbitrarily from
    # `TestGraphQLQueryBasic.test_select_query_author_pk()` using original yaml
    # test case file that we later fixed.
    @pytest.mark.xfail(reason="expected, validating test code")
    def test_tests_detect_bad_ordering(self, hge_ctx):
        """We can detect bad ordering of selection set"""
        check_query_f(hge_ctx, 'test_tests/select_query_author_by_pkey_bad_ordering.yaml', 'http')
        #
        # E           AssertionError:
        # E           expected:
        # E             data:
        # E               author_by_pk:
        # E                 name: Author 1
        # E                 id: 1
        # E           diff: (results differ only in their order of keys)
        # E           response:
        # E             data:
        # E               author_by_pk:
        # E                 id: 1
        # E                 name: Author 1


    # Re-use setup and teardown from where we adapted this test case:
    @classmethod
    def dir(cls):
        return 'queries/graphql_query/basic'


@usefixtures('postgis', 'per_class_tests_db_state')
class TestTests2:
    """
    Test various things about our test framework code. Validate that tests work
    as we expect.
    """

    # Test another bad ordering scenario, while we're here:
    @pytest.mark.xfail(reason="expected, validating test code")
    def test_tests_detect_bad_ordering(self, hge_ctx):
        """We can detect bad ordering of selection set"""
        check_query_f(hge_ctx, 'test_tests/user_can_query_jsonb_values_filter_bad_order.yaml', 'http')
        #
        # E           AssertionError:
        # E           expected:
        # E             data:
        # E               jsonb_table:
        # E               - jsonb_col:
        # E                   name: Hasura
        # E                   age: 7
        # E                 id: 1
        # E           response:
        # E             data:
        # E               jsonb_table:
        # E               - id: 1
        # E                 jsonb_col:
        # E                   age: 7
        # E                   name: Hasura
        # E           diff: (results differ only in their order of keys)


    # Unit test for good measure, to validate above and check our assumptions
    # wrt comparisons of trees of ordered and unordered dicts and arrays:
    def test_tests_dict_ordering_assumptions_and_helpers(self):
        # fragment of yaml test file:
        example_query = {"query": """
            query {
              thing1
              jsonb_table{
                id
                jsonb_col
              }
              thing2
            }
            """ }
        # We want to collapse any ordering we don't care about here
        # (CommentedMap is ruamel.yaml's OrderedMap that also preserves
        # format):
        fully_ordered_result = \
            CommentedMap([('data',
                CommentedMap([
                    ('thing1', "thing1"),
                    ('jsonb_table', [
                        CommentedMap([
                            ('id', 1),
                            ('jsonb_col', CommentedMap([('age', 7), ('name', 'Hasura')]))]),
                        CommentedMap([
                            ('id', 2),
                            ('jsonb_col', CommentedMap([('age', 8), ('name', 'Rawkz')]))]),
                    ]),
                    ('thing2', CommentedMap([("a",1), ("b",2), ("c",3)])),
                ]))])

        relevant_ordered_result = collapse_order_not_selset(fully_ordered_result, example_query)

        # We expect to have discarded ordering of leaves not in selset:
        relevant_ordered_result_expected = \
            dict([('data',
                CommentedMap([
                    ('thing1', "thing1"),
                    ('jsonb_table', [
                        CommentedMap([
                            ('id', 1),
                            ('jsonb_col', dict([('age', 7), ('name', 'Hasura')]))]),
                        CommentedMap([
                            ('id', 2),
                            ('jsonb_col', dict([('age', 8), ('name', 'Rawkz')]))]),
                    ]),
                    ('thing2', dict([("a",1), ("b",2), ("c",3)])),
                ]))])

        # NOTE: use str() to actually do a stong equality comparison, comparing
        # types. Only works because str() on dict seems to have a canonical
        # ordering.
        assert str(relevant_ordered_result) == str(relevant_ordered_result_expected)

        # Demonstrate equality on different mixes of trees of ordered and unordered dicts:
        assert CommentedMap([("a", "a"), ("b", "b")]) ==         dict([("b", "b"), ("a", "a")])
        assert CommentedMap([("a", "a"), ("b", "b")]) != CommentedMap([("b", "b"), ("a", "a")])
        assert         dict([           ("x", CommentedMap([("a", "a"), ("b", CommentedMap([("b1", "b1"), ("b2", "b2")]))])), ("y","y"),]) == \
               CommentedMap([("y","y"), ("x",         dict([("a", "a"), ("b", CommentedMap([("b1", "b1"), ("b2", "b2")]))])), ])

    def test_tests_ordering_differences_correctly_ignored(self, hge_ctx):
        """
        We don't care about ordering of stuff outside the selection set e.g. JSON fields.
        """
        check_query_f(hge_ctx, 'test_tests/user_can_query_jsonb_values_filter_okay_orders.yaml', 'http')

    # Re-use setup and teardown from where we adapted this test case:
    @classmethod
    def dir(cls):
        return 'queries/graphql_query/permissions'

@usefixtures("per_class_tests_db_state")
class TestTests3:

    """
    This test case is about testing validate_http_anyq_with_allowed_responses
    with an empty list of allowed responses wherein it should throw an exception
    """

    @pytest.mark.xfail(reason="expected, validating function working")
    def test_tests_validate_http_anyq_with_allowed_responses_with_empty_list(
        self, hge_ctx
    ):
        # These values are being set as they are in address_not_null_constraint_error.yaml

        url = "/v1/graphql"
        query = {
            "query": 'mutation {\n  insert_address(objects: [{street: "koramangala"}]){\n    returning{\n      id\n      street\n    }\n    affected_rows\n  }\n} \n'
        }

        try:
            resp, pass_test = validate_http_anyq_with_allowed_responses(
                hge_ctx, url, query, {}, 200, []
            )
        except:
            print("FAIL!")
            assert 0, "Test failure, occurs as expected"
        # It reaches here only if the exception wasn't caught, in which case
        # this current test should fail

    """
      This test case is about testing validate_http_anyq_with_allowed_responses
      with a list of allowed responses which are incorrect wherein it should fail the test
    """

    @pytest.mark.xfail(reason="expected, validating test code")
    def test_tests_validate_http_anyq_with_allowed_responses_with_no_correct_response(
        self, hge_ctx
    ):
        # These values are being set as they are in address_not_null_constraint_error.yaml

        url = "/v1/graphql"
        query = {
            "query": 'mutation {\n  insert_address(objects: [{street: "koramangala"}]){\n    returning{\n      id\n      street\n    }\n    affected_rows\n  }\n} \n'
        }
        allowed_response_1 = {
            "response": {
                "errors": [
                    {
                        "extensions": {
                            "code": "constraint-violation",
                            "path": "$.selectionSet.insert_address.args.objects",
                        },
                        "message": 'Not-NULL. null value in column "door_no" violates not-null constraint',
                    }
                ]
            }
        }
        allowed_response_2 = {
            "response": {
                "errors": [
                    {
                        "extensions": {
                            "code": "constraint-violation",
                            "path": "$.selectionSet.insert_address.args.objects",
                        },
                        "message": 'Not-NULL violation. null value in column "door_no" of relation "address" not-null constraint',
                    }
                ]
            }
        }
        allowed_responses = [allowed_response_1, allowed_response_2]

        try:
            resp, err = validate_http_anyq_with_allowed_responses(
                hge_ctx, url, query, {}, 200, allowed_responses
            )
        except:
            print("FAIL!")
            assert 0, "Test failed, as expected"



    # Re-use setup and teardown from where we adapted this test case:
    @classmethod
    def dir(cls):
        return "queries/graphql_mutation/insert/constraints"
