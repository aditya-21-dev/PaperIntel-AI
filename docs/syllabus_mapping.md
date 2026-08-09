# PaperIntel AI — Module 3 syllabus mapping

Module 3 implements deterministic knowledge representation over the structured document produced by Module 2. It does not parse the PDF again and does not evaluate paper quality.

## Implemented syllabus concepts

| Syllabus concept | Module 3 implementation |
| --- | --- |
| Knowledge-Based Agents | `KnowledgeAgent` perceives Module 2 structured input, updates an in-memory knowledge base, and answers exact fact queries. |
| Knowledge Engineering | The engine identifies entities, normalizes generated IDs, creates facts and relationships, preserves evidence, and validates the resulting knowledge base. |
| Knowledge Representation | The paper, authors, abstract, keywords, sections, references, figures, tables, and citations are represented as typed entities. |
| Propositional Logic | Controlled Boolean facts such as `PaperHasAbstract(paper_001)` are stored with arguments, truth values, and evidence. |
| Syntax and Semantics | Entity, fact, relationship, evidence, allowed predicate, and validation schemas are explicit. Undefined predicates and missing graph entities are validation errors. |
| First-Order Logic Representation | Relationships use subject-predicate-object triples and a readable form such as `HasSection(paper_001, section_001)`. |
| Agents based on Propositional Logic | The query endpoint performs deterministic exact lookup of stored propositional facts. |

## Deliberately not implemented yet

The following concepts are reserved for later modules and are **not** claimed as implemented here:

- Forward Chaining
- Backward Chaining
- Resolution
- Model Checking
- Heuristic Search
- Local Search
- Constraint Satisfaction Problems (CSP)
- Game Playing

Module 3 also contains no LLM integration, machine learning, scoring, compliance assessment, citation-quality assessment, or recommendation engine.
