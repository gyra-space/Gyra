import styled from 'styled-components';

export const VisConfirmCardWrap = styled.div`
  @keyframes confirmOptionIn {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  width: 100%;
  min-width: 100px;
  padding: 6px;

  .card-content {
    width: 100%;
    min-width: 100px;
    white-space: pre-wrap;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: flex-start;
    background-color: var(--bg-elev);
    padding: 16px;
    border: 1px solid var(--line-soft);
    border-radius: var(--r-lg);
    box-shadow: var(--sh-card);
  }

  /* ===== Header: icon chip + title + status pill ===== */
  .confirm-header {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
  }

  .confirm-header-icon {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
    color: var(--brand);
    background: var(--brand-soft);
    transition:
      background-color var(--transition),
      color var(--transition);

    &.is-confirmed {
      color: var(--success);
      background: rgba(var(--mcp-success-rgb), 0.12);
    }
  }

  .confirm-title {
    font-size: var(--fs-title);
    color: var(--ink-900);
    line-height: 24px;
    font-weight: 600;
  }

  .confirm-pill {
    margin-left: auto;
    flex-shrink: 0;
    font-size: var(--fs-aux);
    font-weight: 500;
    color: var(--brand);
    background: var(--brand-soft);
    padding: 3px 10px;
    border-radius: 999px;
    white-space: nowrap;
  }

  .confirm-markdown {
    width: 100%;
  }

  .option-section {
    width: 100%;
    margin-top: 2px;
  }

  .confirm-question {
    width: 100%;
    font-size: var(--fs-title);
    font-weight: 600;
    color: var(--ink-900);
    line-height: 1.5;
    margin-bottom: 12px;
  }

  /* ===== Options: radio-affordance cards ===== */
  .option-list {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .option-item {
    width: 100%;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 14px;
    text-align: left;
    font-size: var(--fs-body);
    line-height: 1.5;
    color: var(--ink-700);
    background-color: var(--bg-elev);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    cursor: pointer;
    animation: confirmOptionIn 0.26s var(--ease-expo) both;
    transition:
      border-color var(--transition),
      background-color var(--transition),
      box-shadow var(--transition),
      transform var(--transition);

    &:hover:not(:disabled) {
      border-color: var(--brand);
      background-color: var(--brand-soft);
      transform: translateY(-1px);
      box-shadow: var(--sh-glow);
    }

    &:focus-visible {
      outline: 2px solid var(--brand);
      outline-offset: 2px;
    }

    &.is-selected {
      border-color: var(--brand);
      background-color: var(--brand-soft);
      color: var(--ink-900);

      .option-label {
        color: var(--ink-900);
      }
    }

    &:disabled {
      cursor: not-allowed;
    }

    &:disabled:not(.is-selected) {
      opacity: 0.5;
    }
  }

  .option-item.custom-input-item {
    border-style: dashed;
  }

  /* hollow radio; fills with the brand check when selected */
  .option-radio {
    flex-shrink: 0;
    margin-top: 1px;
    width: 18px;
    height: 18px;
    border-radius: 999px;
    border: 1.5px solid var(--ink-300);
    color: var(--brand);
    font-size: 15px;
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: border-color var(--transition);
  }

  .option-item.is-selected .option-radio {
    border-color: transparent;
  }

  .option-label-wrap {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .option-label {
    font-weight: 600;
    color: var(--ink-800);
  }

  .option-desc {
    font-size: var(--fs-aux);
    color: var(--ink-400);
  }

  .option-hint {
    font-size: var(--fs-aux);
    color: var(--brand);
  }

  .option-input {
    margin-top: 8px;
    padding-left: 4px;

    .ant-input {
      font-size: var(--fs-body);
    }
  }

  .custom-input-area {
    margin-top: 12px;

    .ant-input {
      font-size: var(--fs-body);
    }
  }

  /* ===== Confirmed record: layered, trust-elevated ===== */
  .confirm-record {
    width: 100%;
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(var(--mcp-success-rgb), 0.28);
    border-radius: var(--r-lg);
    background: linear-gradient(
      180deg,
      rgba(var(--mcp-success-rgb), 0.06),
      rgba(var(--mcp-success-rgb), 0.02)
    );
    overflow: hidden;
    animation: confirmOptionIn 0.3s var(--ease-expo) both;

    .confirm-record-head {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 14px;
      border-bottom: 1px solid rgba(var(--mcp-success-rgb), 0.14);

      .confirm-record-avatar {
        width: 28px;
        height: 28px;
        border-radius: 999px;
        flex-shrink: 0;
        overflow: hidden;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
        color: var(--success);
        background: rgba(var(--mcp-success-rgb), 0.18);

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
      }

      .confirm-record-who {
        display: flex;
        flex-direction: column;
        line-height: 1.3;
        min-width: 0;

        .confirm-record-title {
          font-size: var(--fs-body);
          font-weight: 600;
          color: var(--ink-900);
        }

        .confirm-record-time {
          font-size: var(--fs-aux);
          color: var(--ink-400);
        }
      }

      .confirm-record-check {
        margin-left: auto;
        flex-shrink: 0;
        color: var(--success);
        font-size: 18px;
      }
    }

    .confirm-record-body {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 10px 14px 12px;

      .confirm-record-question {
        font-size: var(--fs-aux);
        color: var(--ink-500);
      }

      .confirm-record-answer {
        font-size: var(--fs-body);
        font-weight: 600;
        color: var(--ink-900);
        background: var(--bg-elev);
        border: 1px solid var(--line-soft);
        border-radius: var(--r-sm);
        padding: 8px 10px;
      }
    }
  }

  /* ===== Footer ===== */
  .confirm-footer {
    width: 100%;
    min-height: 36px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
  }

  .confirm-button {
    height: 34px;
    padding: 0 18px;
    border-radius: var(--r-md) !important;
    font-weight: 500;
  }

  .confirm-button.ant-btn-primary {
    background: linear-gradient(180deg, #6366f1, #4f46e5);
    border-color: transparent;
    box-shadow: 0 1px 2px rgba(var(--brand-rgb), 0.2);
  }

  .confirm-button.ant-btn-primary:not(:disabled):hover {
    background: linear-gradient(180deg, #7177f5, #5546ef);
    border-color: transparent;
  }

  .confirm-status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-left: auto;
    padding: 4px 12px 4px 9px;
    font-size: var(--fs-body);
    color: var(--ink-500);
    background: rgba(var(--mcp-success-rgb), 0.08);
    border: 1px solid rgba(var(--mcp-success-rgb), 0.2);
    border-radius: 999px;

    .confirm-status-dot {
      color: var(--success);
      font-size: 15px;
      display: inline-flex;
    }

    .confirm-status-text {
      font-weight: 500;
    }
  }
`;