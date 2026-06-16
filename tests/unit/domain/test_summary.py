from __future__ import annotations

from src.domain.entities.summary import Summary, SummaryStatus


class TestSummary:
    def test_default_status_is_pending(self):
        s = Summary(article_id="a1", model_version="v1")
        assert s.status == SummaryStatus.PENDING

    def test_auto_generated_id(self):
        s = Summary(article_id="a1", model_version="v1")
        assert len(s.id) == 36

    def test_summary_status_string_values(self):
        assert SummaryStatus.PENDING.value == "pending"
        assert SummaryStatus.PROCESSING.value == "processing"
        assert SummaryStatus.COMPLETED.value == "completed"
        assert SummaryStatus.FAILED.value == "failed"

    def test_completed_summary_has_text(self):
        s = Summary(
            article_id="a1",
            model_version="v1",
            text="Some summary.",
            status=SummaryStatus.COMPLETED,
        )
        assert s.text == "Some summary."
        assert s.status == SummaryStatus.COMPLETED
