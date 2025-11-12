# Annotation Instructions for Experts

## *Objective*
Create a clear, step-by-step annotation that mirrors your own problem-solving thought process.
This annotation will be given to an expert LLM to guide a student LLM to solve the problem, thereby efficiently generating training data.

### 1. Present the Problem
- Clearly state the problem wihtout ambiguity
- Text only for now

### 2. Break Down Your Thought Process
- For every problem, divide your thought process into steps.
- Label each step (Step 1, Step 2, …) to create a clear and logical flow.

### 3. For Each Step, Include the Following Details:

- **Step description:**  
  Clearly state the task or question for this step.  
  *Example:* "Read the problem to identify inputs, allowed operations, and outputs."

- **Answer:**  
  Provide the ideal answer for the step, which can be a number, an expression or a statement.  
  *Example:* "The array can be reduced to all zeros in at most 2 operations."

- **Substeps:**  
  If the step is complex, break it down into smaller parts.  
  *Format:* Use bullet points or nested numbering.  
  *Example:*  
  - Identify the input for each test case.  
  - Determine the allowed operations on the array.  
  - Outline the expected output for each case.

- **Hints:**  
  Provide 1–3 hints to encourage the model to think through the step before revealing the answer.  
  *Example:*
  - "What happens if you select the entire array?"  
  - "Is it possible to reduce the array to zeros in fewer operations?"