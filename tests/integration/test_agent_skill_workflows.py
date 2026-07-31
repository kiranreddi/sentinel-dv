"""End-to-end validation for the published Sentinel DV agent skills."""

from scripts.verify_skill_workflows import verify_skill_workflows


def test_published_skill_workflows() -> None:
    result = verify_skill_workflows()

    assert result["regression_triage"]["clusters"] >= 1
    assert result["failure_debugging"]["waveform_format"] == "vcd-summary"
    assert result["coverage_closure"]["candidate_sv_validated"] is True
