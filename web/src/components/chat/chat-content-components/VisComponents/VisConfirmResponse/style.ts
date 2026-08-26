import styled from 'styled-components';

export const VisConfirmResponseWrap = styled.div`
  width: 100%;
  padding: 4px 6px;

  .response-card {
    position: relative;
    overflow: hidden;
    background: linear-gradient(
      180deg,
      rgba(var(--mcp-success-rgb), 0.07),
      rgba(var(--mcp-success-rgb), 0.02)
    );
    border: 1px solid rgba(var(--mcp-success-rgb), 0.28);
    border-radius: var(--r-lg);
    padding: 12px 16px 12px 20px;

    /* left trust accent */
    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 10px;
      bottom: 10px;
      width: 3px;
      border-radius: 999px;
      background: var(--success);
    }

    .response-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;

      .check-icon {
        color: var(--success);
        font-size: 17px;
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
      margin-bottom: 10px;
      padding: 8px 10px;
      font-size: var(--fs-body);
      color: var(--ink-500);
      background: var(--bg-elev);
      border: 1px solid var(--line-soft);
      border-radius: var(--r-sm);
    }

    .response-content {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .response-selection {
        display: flex;
        align-items: center;
        gap: 8px;

        .selection-tag {
          font-size: var(--fs-body);
          font-weight: 500;
          color: var(--brand) !important;
          border-color: rgba(var(--brand-rgb), 0.4) !important;
          background-color: rgba(var(--brand-rgb), 0.08) !important;
          border-radius: 8px;
        }

        .selection-desc {
          font-size: var(--fs-aux);
          color: var(--ink-400);
        }
      }

      .response-input {
        font-size: var(--fs-body);
        color: var(--ink-700);
      }
    }
  }
`;