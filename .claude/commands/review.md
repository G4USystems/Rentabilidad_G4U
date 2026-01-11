# Code Review & Verification

Please go back and verify all your work so far, making sure you used best coding practices, were efficient, and maintained good security.

## Instructions

Review all implementations and verify:

### 1. Code Quality
- Check for code duplication - consolidate repeated logic into functions
- Verify proper error handling with try/catch blocks
- Ensure consistent naming conventions
- Look for unused variables or dead code
- Verify functions are not too long (break down if > 50 lines)

### 2. Security
- No hardcoded secrets, API keys, or passwords
- Input validation on all user inputs
- SQL injection prevention (parameterized queries)
- XSS prevention (proper escaping of user content)
- CORS properly configured for production
- Authentication/authorization checks on protected endpoints

### 3. Performance
- No N+1 query problems
- Proper use of async/await where applicable
- Avoid unnecessary API calls or database queries
- Check for memory leaks (unclosed connections, event listeners)

### 4. Bug Prevention
- Edge cases handled (null, undefined, empty arrays)
- Proper type checking where needed
- API error responses handled gracefully
- UI states for loading, error, and empty data

### 5. Testing
- Manually test critical user flows
- Verify error messages are user-friendly
- Check responsive behavior if applicable

## Output

Provide a summary of:
1. Issues found (categorized by severity: Critical, High, Medium, Low)
2. Fixes applied
3. Recommendations for future improvements
