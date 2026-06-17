"""The CrewAI Flow that connects the two crews (the assignment's spine).

START -> Crew 1 (Recipe Analyst) -> VALIDATION CHECKPOINT (clean_data vs
contract) -> Crew 2 (Recipe Scientist) -> FINISH. If validation fails the Flow
halts gracefully and Crew 2 never runs.

Run locally to (re)generate the 8 artifacts:
    pip install -r requirements-dev.txt
    python -m pipeline.flow
"""

from __future__ import annotations

import json
import logging

import pandas as pd
from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

from . import tools as T
from .crews import analyst_crew, scientist_crew

logging.basicConfig(level=logging.INFO, format="[flow] %(message)s")
log = logging.getLogger("suchef.flow")


class PipelineState(BaseModel):
    problems: list[str] = []
    valid: bool = False


class SuChefFlow(Flow[PipelineState]):
    """Two crews + automated handoff + contract validation + graceful failure."""

    @start()
    def run_analyst_crew(self):
        log.info("Crew 1 (Recipe Analyst) starting…")
        analyst_crew().kickoff()
        log.info("Crew 1 finished — clean_data.csv, eda_report.html, "
                 "insights.md, dataset_contract.json written.")

    @router(run_analyst_crew)
    def validate_contract(self):
        """Validation checkpoint: clean_data.csv must match dataset_contract.json
        before the modelling crew is allowed to run."""
        df = pd.read_csv(T.CLEAN_CSV)
        contract = json.loads(T.CONTRACT_JSON.read_text(encoding="utf-8"))
        problems = T.validate_clean_against_contract(df, contract)
        self.state.problems = problems
        if problems:
            log.error("VALIDATION FAILED — " + "; ".join(problems))
            return "invalid"
        self.state.valid = True
        log.info("VALIDATION PASSED — clean_data matches the contract.")
        return "valid"

    @listen("valid")
    def run_scientist_crew(self):
        log.info("Crew 2 (Recipe Scientist) starting…")
        scientist_crew().kickoff()
        feats = pd.read_csv(T.FEATURES_CSV)
        fproblems = T.validate_features(feats)
        if fproblems:
            raise ValueError("Feature validation failed: " + "; ".join(fproblems))
        log.info("Crew 2 finished — features.csv, model.pkl, "
                 "evaluation_report.md, model_card.md written.")
        log.info("PIPELINE COMPLETE — all 8 artifacts in artifacts/.")

    @listen("invalid")
    def halt(self):
        log.error("PIPELINE HALTED — contract validation failed; Crew 2 skipped. "
                  "Problems: " + "; ".join(self.state.problems))


def _load_key_into_env() -> None:
    """CrewAI/litellm needs ANTHROPIC_API_KEY in the environment; read it from
    .streamlit/secrets.toml if it isn't already set."""
    import os
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    secrets = T._ROOT / ".streamlit" / "secrets.toml"
    if secrets.exists():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY"):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
                break


if __name__ == "__main__":
    _load_key_into_env()
    SuChefFlow().kickoff()
