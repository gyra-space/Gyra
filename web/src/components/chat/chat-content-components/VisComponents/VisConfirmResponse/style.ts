import styled from 'styled-components';

export const VisConfirmResponseWrap = styled.div`
  width: 100%;
  padding: 4px 6px;

  .response-card {
    background: rgba(var(--mcp-success-rgb), 0.1);
    border: 1px solid rgba(var(--mcp-success-rgb), 0.35);
    border-radius: var(--r-md);
    padding: 12px 16px;

    .response-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;

      .check-icon {
        color: var(--success);
        font-size: 16px;
      }

      .response-title {
        font-size: var(--fs-title);
        color: var(--ink-900);
        font-weight: 600;
      }

      .response-time {
        margin-left: auto;
        font-size: var(--fs-aux);
        color: var(--ink-400);
      }
    }

    .response-question {
      margin-bottom: 8px;
      font-size: var(--fs-body);
      color: var(--ink-500);
    }

    .response-content {
      .response-selection {
        display: flex;
        align-items: center;
        gap: 8px;

        .selection-tag {
          font-size: var(--fs-body);
          color: var(--brand) !important;
          border-color: rgba(var(--brand-rgb), 0.4) !important;
          background-color: rgba(var(--brand-rgb), 0.08) !important;
        }

        .selection-desc {
          font-size: var(--fs-aux);
          color: var(--ink-400);
        }
      }

      .response-input {
        margin-top: 4px;
        font-size: var(--fs-body);
        color: var(--ink-700);
      }
    }
  }
`;
