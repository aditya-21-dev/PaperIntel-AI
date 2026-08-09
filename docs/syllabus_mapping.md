# PaperIntel AI — Modules 3 and 4 syllabus mapping

Module 3 implements deterministic knowledge representation over the structured document produced by Module 2. Module 4 consumes only that structured knowledge base for rule-based reasoning; it does not parse the PDF again, duplicate knowledge engineering, or evaluate paper quality.

## Module 3: implemented syllabus concepts

| Syllabus concept | Module 3 implementation |
| --- | --- |
| Knowledge-Based Agents | `KnowledgeAgent` perceives Module 2 structured input, updates an in-memory knowledge base, and answers exact fact queries. |
| Knowledge Engineering | The engine identifies entities, normalizes generated IDs, creates facts and relationships, preserves evidence, and validates the resulting knowledge base. |
| Knowledge Representation | The paper, authors, abstract, keywords, sections, references, figures, tables, and citations are represented as typed entities. |
| Propositional Logic | Controlled Boolean facts such as `PaperHasAbstract(paper_001)` are stored with arguments, truth values, and evidence. |
| Syntax and Semantics | Entity, fact, relationship, evidence, allowed predicate, and validation schemas are explicit. Undefined predicates and missing graph entities are validation errors. |
| First-Order Logic Representation | Relationships use subject-predicate-object triples and a readable form such as `HasSection(paper_001, section_001)`. |
| Agents based on Propositional Logic | The query endpoint performs deterministic exact lookup of stored propositional facts. |

## Module 4: implemented syllabus concepts

| Syllabus concept | Module 4 implementation |
| --- | --- |
| Knowledge-Based Agents | `ReasoningAgent` perceives a validated Module 3 knowledge base, loads its facts, applies rules, answers goals, and returns explanations. |
| Propositional Logic reasoning | Facts preserve explicit Boolean values. The engine distinguishes known true, known false, and unknown facts. |
| Forward Chaining | A generic fixed-point engine applies the data-defined rule base until no new conclusions can be derived or a safety limit is reached. |
| Backward Chaining | A separate goal-driven engine recursively checks rules and premises for a requested conclusion. |
| Rule-Based Inference | Rules contain identifiers, premises, conclusions, priorities, explanations, and source-module metadata; inference logic does not special-case paper rules. |
| Explainable Knowledge-Based Reasoning | Forward rule firings and backward proof attempts retain rule IDs, supporting facts, missing facts, known false facts, and human-readable explanations. |

Module 4’s only reasoning input is the Module 3 knowledge base. Derived facts are returned separately from the source knowledge base so later modules can consume both without PDF reparsing.

## Deliberately not implemented yet

The following concepts are reserved for later modules and are **not** claimed as implemented here:

- Resolution
- Model Checking
- Heuristic Search
- Local Search
- Constraint Satisfaction Problems (CSP)
- Game Playing
- Alpha-Beta pruning

Modules 3 and 4 also contain no LLM integration, machine learning, scoring, compliance assessment, citation-quality assessment, or recommendation engine.
