# CLAUDE.md

## Project Context
This project is a React application written in **TypeScript**.
Code should be production-quality, readable, and maintainable.

---

## General Rules
- Prefer **clarity over cleverness**
- Follow existing project patterns before introducing new ones
- Do not introduce new dependencies unless explicitly requested
- Avoid premature optimization

---

## TypeScript Rules
- Always use **TypeScript**, never `any` unless explicitly justified
- Prefer `type` over `interface` unless extension is required
- Enable and respect strict type checking
- Use explicit return types for exported functions
- Avoid type assertions (`as`) unless unavoidable

---

## React Rules
- Use **function components only**
- Prefer **React hooks** over class patterns
- Keep components **small and focused**
- One component per file (unless tightly coupled)
- Use **PascalCase** for components and **camelCase** for props and functions

---

## Hooks & State
- Follow the **Rules of Hooks**
- Prefer local state over global state
- Use `useMemo` and `useCallback` only when there is a real performance reason
- Avoid deeply nested state objects
- Extract complex logic into custom hooks

---

## Styling
- Follow the existing styling approach Tailwind
- Avoid inline styles unless necessary
- Prefer semantic HTML elements

---

## File & Folder Structure
- Group files by **feature**, not by type, when possible
- Keep imports ordered:
  1. External libraries
  2. Internal modules
  3. Relative imports
- Remove unused files, imports, and variables

---

## Testing
- Prefer **unit tests** for logic
- Prefer **integration tests** for components
- Use clear, descriptive test names
- Tests should focus on behavior, not implementation details

---

## Accessibility (a11y)
- Use semantic HTML
- Ensure form inputs have associated labels
- Add `aria-*` attributes when necessary
- Do not disable accessibility lint rules

---

## Performance
- Avoid unnecessary re-renders
- Lazy-load routes and heavy components where appropriate
- Avoid anonymous functions in render when not needed

---

## Comments & Documentation
- Comment **why**, not what
- Avoid redundant comments
- Update documentation when behavior changes

---

## Error Handling
- Handle loading and error states explicitly
- Do not swallow errors silently
- Prefer user-friendly error messages

---

## Code Output Expectations
When generating or modifying code:
- Match existing formatting and conventions
-No files over 500 lines
- Provide complete, working examples
- Do not leave TODOs unless explicitly requested

## Project Requirements
-All types should be stored in the types directory. Not in components.
-All API calls should be stored in the service directory. Not in components.
