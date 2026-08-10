# PaperIntel AI — Modules 3, 4, and 5 syllabus mapping

Modules 3–5 form a deterministic knowledge pipeline. Module 3 creates the in-memory knowledge base from Module 2 structured extraction. Module 4 derives facts through rule-based inference. Module 5 verifies propositions semantically and by propositional resolution; it does not parse PDFs, introduce persistence, or replace Module 4’s inference algorithms.

## Module 3: implemented syllabus concepts

| Syllabus concept | Module 3 implementation |
| --- | --- |
| Knowledge-Based Agents | `KnowledgeAgent` perceives Module 2 structured input, updates an in-memory knowledge base, and answers exact fact queries. |
| Knowledge Engineering | The engine identifies entities, normalizes generated IDs, creates facts and relationships, preserves evidence, and validates the resulting knowledge base. |
| Knowledge Representation | The paper, authors, abstract, keywords, sections, references, figures, tables, and citations are represented as typed entities. |
| Propositional Logic | Controlled Boolean facts such as `PaperHasAbstract(paper_001)` are stored with arguments, truth values, and evidence. |
| Syntax and Semantics | Entity, fact, relationship, evidence, allowed predicate, and validation schemas are explicit. Undefined predicates and missing graph entities are validation errors. |
| First-Order Logic Representation | Relationships use subject-predicate-object triples and a readable form such as `HasSection(paper_001, section_001)`. |

## Module 4: implemented syllabus concepts

| Syllabus concept | Module 4 implementation |
| --- | --- |
| Knowledge-Based Agents | `ReasoningAgent` perceives a validated Module 3 knowledge base, loads facts, applies rules, answers goals, and returns explanations. |
| Rule-Based Inference | Rules contain identifiers, premises, conclusions, priorities, explanations, and source-module metadata; inference logic does not special-case paper rules. |
| Forward Chaining | A generic fixed-point engine applies data-defined rules until no new conclusions can be derived or a safety limit is reached. |
| Backward Chaining | A separate goal-driven engine recursively checks rules and premises for a requested conclusion. |
| Explainable Knowledge-Based Reasoning | Rule firings and proof attempts retain rule IDs, supporting facts, missing facts, known false facts, and human-readable explanations. |

## Module 5: implemented syllabus concepts

| Syllabus concept | Module 5 implementation |
| --- | --- |
| Propositional Logic | Validated immutable formula ASTs support atoms, NOT, AND, OR, implication, and biconditional; a deterministic evaluator assigns Boolean truth values. |
| Propositional Theorem Proving | The engine checks a query and its negation through refutation, returning `ENTAILED`, `CONTRADICTED`, or `UNKNOWN` when the KB is consistent. |
| Model Checking | Bounded exhaustive model checking evaluates the query in every Boolean model satisfying the supplied Module 3/4 propositions. |
| Resolution | Formulas are converted to CNF through implication elimination, NNF, and distribution. Structured literals and clauses are saturated by resolution with proof traces, pair de-duplication, and safety limits. |
| Logical Consistency | Resolution determines whether the propositional clause set is satisfiable and reports direct unit conflicts or an empty-clause proof of inconsistency. |
| Agents Based on Propositional Logic | `LogicAgent` converts Module 3 facts and Module 4 derived facts into propositions while retaining Module 4 rules and traces in the verification result. |

Module 5’s input remains entirely in memory. It does not configure or require MongoDB, use LLMs or machine learning, or reparse a PDF.

## Deliberately not implemented yet

The following concepts are reserved for later modules and are **not** claimed as implemented here:

- First-order logic theorem proving
- Constraint Satisfaction Problems (CSP) or constraint propagation
- Heuristic or local search
- Game playing or Alpha-Beta pruning
- Machine learning, training datasets, or external LLM reasoning
