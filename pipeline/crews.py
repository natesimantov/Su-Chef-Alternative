"""The two CrewAI crews for the Su Chef data pipeline.

- Crew 1 (Recipe Analyst): loads + cleans the dataset, runs EDA, writes the
  dataset contract, and reports business insights.
- Crew 2 (Recipe Scientist): engineers features, trains + compares models, and
  writes the model card.

The agents do their work through **tools** that wrap the deterministic functions
in `tools.py`, so the heavy lifting is reproducible while the agents orchestrate
and narrate. The crews communicate the assignment-required way: Crew 1 writes
files to `artifacts/`, Crew 2 reads them.
"""

from __future__ import annotations

import json
import os

import pandas as pd
from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

from . import tools as T


def _llm() -> LLM:
    return LLM(model="anthropic/claude-sonnet-4-6",
               api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
               temperature=0.2)


# --- Tools (thin wrappers over the deterministic pipeline) -------------------

@tool("clean_recipe_dataset")
def clean_recipe_dataset() -> str:
    """Load the raw Kaggle recipe CSV and write the cleaned dataset to
    artifacts/clean_data.csv. Returns a one-line summary."""
    df = T.load_and_clean()
    return f"Cleaned {len(df)} recipes -> artifacts/clean_data.csv"


@tool("run_eda_report")
def run_eda_report() -> str:
    """Run exploratory data analysis on the cleaned data and write
    artifacts/eda_report.html. Returns the key stats as JSON."""
    df = pd.read_csv(T.CLEAN_CSV)
    stats = T.run_eda(df)
    T.write_insights(stats)
    return json.dumps(stats)


@tool("write_dataset_contract")
def write_dataset_contract() -> str:
    """Write artifacts/dataset_contract.json (schema, allowed values,
    constraints) that the Data Scientist crew must obey."""
    df = pd.read_csv(T.CLEAN_CSV)
    c = T.write_contract(df)
    return f"Wrote dataset_contract.json ({len(c['schema'])} columns, target {c['target']})"


@tool("validate_dataset")
def validate_dataset() -> str:
    """Validate the cleaned dataset against the data contract (and the engineered
    features, if already built) before modelling. Returns a pass/fail report."""
    df = pd.read_csv(T.CLEAN_CSV)
    contract = json.loads(T.CONTRACT_JSON.read_text(encoding="utf-8"))
    problems = T.validate_clean_against_contract(df, contract)
    if T.FEATURES_CSV.exists():
        problems += T.validate_features(pd.read_csv(T.FEATURES_CSV))
    if problems:
        return "VALIDATION FAILED: " + "; ".join(problems)
    return (f"Validation passed: clean_data matches the contract "
            f"({len(df)} rows, target {contract['target']}).")


@tool("engineer_features")
def engineer_features() -> str:
    """Read cleaned data, build the modelling table (ingredient text + structure
    features and the per-serving nutrition targets), and write
    artifacts/features.csv. Returns a summary."""
    df = pd.read_csv(T.CLEAN_CSV)
    feats = T.engineer_features(df)
    return f"Wrote features.csv {feats.shape} (targets: {', '.join(T.TARGETS)})"


@tool("train_and_compare_models")
def train_and_compare_models() -> str:
    """Train and compare two multi-output regressors on features.csv, save the
    best to artifacts/model.pkl, write evaluation_report.md, and write the model
    card. Returns the metrics as JSON."""
    feats = pd.read_csv(T.FEATURES_CSV)
    info = T.train_and_evaluate(feats)
    info["rows"] = int(len(feats))
    T.write_model_card(info)
    return json.dumps(info)


# --- Crew 1 — Recipe Analyst -------------------------------------------------

def analyst_crew() -> Crew:
    llm = _llm()
    loader = Agent(role="Data Loader",
                   goal="Load and clean the raw recipe dataset reliably.",
                   backstory="A meticulous data engineer who turns messy CSVs "
                             "into clean, typed tables.",
                   tools=[clean_recipe_dataset], llm=llm, verbose=False)
    analyst = Agent(role="Exploratory Data Analyst",
                    goal="Understand what drives recipe cooking time and surface "
                         "clear business insights.",
                    backstory="A data analyst who lets the charts tell the story.",
                    tools=[run_eda_report], llm=llm, verbose=False)
    contractor = Agent(role="Data Contract Author",
                       goal="Codify the cleaned dataset's schema and rules for "
                            "the modelling crew.",
                       backstory="An engineer who writes the data contract other "
                                 "teams build against.",
                       tools=[write_dataset_contract], llm=llm, verbose=False)
    t1 = Task(description="Use the clean_recipe_dataset tool to load and clean "
                          "the data.",
              expected_output="Confirmation that clean_data.csv was written.",
              agent=loader)
    t2 = Task(description="Use the run_eda_report tool, then summarise the 3 most "
                          "important findings about recipe cooking time in plain "
                          "business language.",
              expected_output="A short bullet summary of key EDA findings.",
              agent=analyst)
    t3 = Task(description="Use the write_dataset_contract tool to record the "
                          "schema and rules for the Data Scientist crew.",
              expected_output="Confirmation that dataset_contract.json was written.",
              agent=contractor)
    return Crew(agents=[loader, analyst, contractor], tasks=[t1, t2, t3],
                process=Process.sequential, memory=False, verbose=False)


# --- Crew 2 — Recipe Scientist -----------------------------------------------

def scientist_crew() -> Crew:
    llm = _llm()
    validator = Agent(role="Data Validator",
                      goal="Guarantee the cleaned data obeys the data contract "
                           "before any modelling begins.",
                      backstory="A QA-minded data scientist who refuses to model "
                                "on inputs that violate the contract.",
                      tools=[validate_dataset], llm=llm, verbose=False)
    engineer = Agent(role="Feature Engineer",
                     goal="Turn cleaned recipes into model-ready features.",
                     backstory="An ML engineer who crafts features that capture "
                               "how involved a recipe is.",
                     tools=[engineer_features], llm=llm, verbose=False)
    trainer = Agent(role="Model Trainer & Evaluator",
                    goal="Train and compare models that predict whether a recipe "
                         "is quick, and document the winner.",
                    backstory="A pragmatic data scientist who values honest "
                              "metrics and clear model cards.",
                    tools=[train_and_compare_models], llm=llm, verbose=False)
    t0 = Task(description="Use the validate_dataset tool to confirm the cleaned "
                          "dataset matches the data contract before modelling.",
              expected_output="A validation pass/fail report.",
              agent=validator)
    t1 = Task(description="Use the engineer_features tool to build features.csv "
                          "from the cleaned data.",
              expected_output="Confirmation that features.csv was written.",
              agent=engineer)
    t2 = Task(description="Use the train_and_compare_models tool, then explain in "
                          "a few sentences which model won and what its metrics "
                          "mean for the business.",
              expected_output="A short explanation of the model comparison.",
              agent=trainer)
    return Crew(agents=[validator, engineer, trainer], tasks=[t0, t1, t2],
                process=Process.sequential, memory=False, verbose=False)
