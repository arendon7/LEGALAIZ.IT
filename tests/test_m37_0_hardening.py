from __future__ import annotations

import inspect
import unittest

import core_v11 as core
from legalai_platform.m24_case_journey import M24CaseJourneyCenter
from legalai_platform.post_delivery_followup_m37_0 import (
    PostDeliveryFollowUpCenter,
    PostDeliveryFollowUpError,
)


class M370HardeningTests(unittest.TestCase):
    def setUp(self):
        self.journey = M24CaseJourneyCenter(core.ROOT)
        self.center = PostDeliveryFollowUpCenter(self.journey)

    def test_live_task_validation_is_independent_from_database_row_order(self):
        product = "CO-CD-003"
        labels = list(self.center._task_contracts(product))
        followups = [
            {"id": f"TASK-{index}", "action_label": label}
            for index, label in enumerate(labels, 1)
        ]
        reversed_rows = list(reversed(followups))
        ordered_ids = self.center._validate_live_tasks(product, reversed_rows)
        expected_by_label = {row["action_label"]: row["id"] for row in followups}
        self.assertEqual(ordered_ids, [expected_by_label[label] for label in labels])

    def test_duplicate_task_label_fails_closed(self):
        product = "CO-CD-003"
        labels = list(self.center._task_contracts(product))
        followups = [
            {"id": f"TASK-{index}", "action_label": label}
            for index, label in enumerate(labels, 1)
        ]
        followups[-1] = {"id": "TASK-DUP", "action_label": labels[0]}
        with self.assertRaises(PostDeliveryFollowUpError) as caught:
            self.center._validate_live_tasks(product, followups)
        self.assertEqual(caught.exception.code, "FOLLOWUP_TASK_DRIFT")

    def test_finalize_start_has_no_hidden_commit_and_start_owns_commit_boundary(self):
        finalize_source = inspect.getsource(PostDeliveryFollowUpCenter._finalize_start)
        start_source = inspect.getsource(PostDeliveryFollowUpCenter.start)
        self.assertNotIn(".commit(", finalize_source)
        finalize_call = start_source.index("self._finalize_start(con, enrollment, actor)")
        commit_call = start_source.index("con.commit()", finalize_call)
        detail_call = start_source.index("self._detail_from_open_connection", finalize_call)
        self.assertLess(finalize_call, commit_call)
        self.assertLess(commit_call, detail_call)


if __name__ == "__main__":
    unittest.main()
