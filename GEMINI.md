REQUIRED:
- Whenever significat enhancements, feature upgrades/implementations or bugfixes are done ensure to update knowledge base, and the projects README and CHANGELOG if applicable.

- There are project specific rules and skills located in .claude/skills and .claude/rules that you can use to aid in tasks

**Version**: v3.6.2 (Phoenix Rising)  
- Any updates done should be considered part of v3.7.0 unless its a minor patch

- NEVER JUST START MAKING ANY CHANGES! YOU MUST ALWAYS CREATE A COMPREHENSIVE PLAN IN ORDER TO PERFORM WHATEVER TASK IS ASKED OF YOU!
- IF YOU NEED TO FIX A PROBLEM THEN YOU MUST CREATE A PLAN THAT COMPREHENSIVELY DETAILS THE PROBLEM PROVIDING EVIDENCE AND A SOLUTION AND WAIT FOR REVIEW

- Whenever making frontend/UI edits ensure that the frontend builds successfully without errors.
- Also verify and ensure that the changes does not break any existing functionality.
- The frontend uses React (functional components), Typescript, and MUI components. Use these for all UI modifications.
- Ensure that the components are responsive and works on different screen sizes.
- NEVER GUESS OR INFER. If you are unsure about anything, ask for clarification. ESPECIALLY API FIELDS. LOOK AT THE BACKEND CODE TO UNDERSTAND THE FIELDS. NEVER GUESS OR INFER.
- Always ensure to update the required documentation after making changes.
- All backend functions must have comprehensive inline comments describing the required variables and what the function does.
- All frontend components should have real-time UI updates where applicable.
- All new components must be created in the components directory.
- Any component created must be placed in the directory it belongs to based on the functionality of the component.
- Any new component created must have documentation created for it in the documentation directory.
- Always save knowledge base when make decisions or deciding on specific coding patterns or when creating new components.
- Whenever you are asked to implement a new feature ensure to save that to your knowledge base when a full understanding of the implementation is achieved.
- Whenever a feature has been fully implemented ensure that all documentation is updated to reflect the changes.
- When a feature is implemented ensure to update your knowledge base and save it. This will help improve performance of future implementations. This step is very important. When you are done with an implementation ensure that you have saved the knowledge base.
- Whenever you do not have a full understand of something ensure to propery analyze the codebase and gain a full understanding of it, then save it to your knowledge base before and after making changes. This step is very important.

- All functions should have detailed inline comments to ensure clarity and understanding of the code.
-- eg:
```python
    """Fetch URLs using different tools like gauplus, gau, gospider, waybackurls ...

	Args:
		urls (list): List of URLs to start from.
		description (str, optional): Task description shown in UI.
	"""
```

RUNTIME:
- All runtime tasks and processes run within the docker containers in both dev and production.
- All backend and frontend code is located locally but testing and runtime is contained within the docker containers.
