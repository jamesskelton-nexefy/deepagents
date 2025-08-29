# Frontend Context ID Integration Guide

## Overview

The backend document tools (`list_documents`, `search_documents`, `retrieve_document`) now require a context ID to scope operations to the current conversation. This document outlines the required frontend changes.

## Key Change Required

**Pass `contextId` in the LangGraph agent state for every agent invocation.**

## Implementation

### Before (Current)
```javascript
// Current frontend call
agent.invoke({
    "messages": [{ role: "user", content: userMessage }]
})
```

### After (Required)
```javascript
// Updated frontend call
agent.invoke({
    "messages": [{ role: "user", content: userMessage }],
    "contextId": threadId  // Add this line - use existing thread ID
})
```

## Detailed Implementation

### 1. Thread ID Source
- Use the **same `threadId`** already being used for LangGraph conversation persistence
- This is the UUID that identifies the current conversation/thread
- **No new ID generation required**

### 2. When to Include contextId
- **Every time** `agent.invoke()` is called
- Include it in the initial state object alongside messages
- Required for both new conversations and continuing existing ones

### 3. Property Requirements
- **Property name:** Must be exactly `"contextId"` (camelCase)
- **Data type:** String (UUID)
- **Required:** Yes, for document tools to function

### 4. Example Implementation

```javascript
// Complete example function
function invokeAgent(userMessage, threadId) {
    const state = {
        messages: [{ role: "user", content: userMessage }],
        contextId: threadId  // Add this line
    };
    
    return agent.invoke(state, {
        configurable: { thread_id: threadId }  // Existing LangGraph config
    });
}

// Usage example
const threadId = "550e8400-e29b-41d4-a716-446655440000"; // Your existing thread ID
const response = await invokeAgent("List my documents", threadId);
```

### 5. React/TypeScript Example

```typescript
interface AgentState {
    messages: Message[];
    contextId: string;  // Add this to your state interface
}

const invokeAgent = async (message: string, threadId: string) => {
    const state: AgentState = {
        messages: [{ role: "user", content: message }],
        contextId: threadId
    };
    
    return await agent.invoke(state, {
        configurable: { thread_id: threadId }
    });
};
```

## Benefits After Implementation

✅ **Document Listing:** `list_documents` tool will show documents in current conversation  
✅ **Document Search:** `search_documents` will be scoped to current conversation's documents  
✅ **Document Retrieval:** `retrieve_document` can find documents by filename within conversation  
✅ **Document Processing:** New documents will be associated with correct conversation context  
✅ **Context Isolation:** Each conversation has its own document space  

## What Doesn't Change

❌ **No API endpoint changes** - Same endpoints, same authentication  
❌ **No new environment variables** - Use existing configuration  
❌ **No database changes** - Backend handles context mapping  
❌ **No thread ID generation changes** - Use existing thread management  

## Error Handling

If `contextId` is missing from the agent state, document tools will return clear error messages:

```json
{
  "error": "context_id is required to list documents. Please provide the current conversation context ID.",
  "success": false
}
```

## Testing Checklist

After implementing the change, verify:

1. **✅ Agent invocation includes contextId**
   ```javascript
   console.log(state); // Should show: { messages: [...], contextId: "uuid" }
   ```

2. **✅ Document tools work in agent**
   - Agent can respond to: "List my documents"
   - Agent can respond to: "Search for documents about X"
   - Agent can respond to: "Show me the content of document.pdf"

3. **✅ Context isolation**
   - Documents uploaded in one conversation don't appear in another
   - Each thread has its own document space

## Troubleshooting

### Issue: "context_id is required" error
**Solution:** Ensure `contextId` is included in every `agent.invoke()` call

### Issue: Agent can't find documents
**Solution:** Verify `threadId` being passed is the same one used when documents were uploaded

### Issue: Documents appearing in wrong conversation
**Solution:** Check that unique `threadId` is used for each conversation

## Implementation Priority

**🔴 High Priority:** Required for document tools to function properly

**📅 Timeline:** Should be implemented before users start uploading documents to conversations

## Support

If you encounter issues during implementation:
1. Verify the `contextId` is being passed correctly in agent state
2. Check browser console for any error messages
3. Confirm `threadId` matches the conversation thread
4. Test with a simple "List my documents" command

---

**Summary:** Add `"contextId": threadId` to every `agent.invoke()` call alongside existing messages.
