import styled from 'styled-components';

export const VisConfirmCardWrap = styled.div`
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

  .confirm-title {
    font-size: var(--fs-title);
    color: var(--ink-900);
    line-height: 24px;
    font-weight: 600;
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

  .option-list {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .option-item {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 14px;
    text-align: left;
    font-size: var(--fs-body);
    line-height: 1.5;
    color: var(--ink-700);
    background-color: var(--bg-elev);
    border: 1px solid var(--line-soft);
    border-radius: var(--r-md);
    cursor: pointer;
    transition:
      border-color var(--transition),
      background-color var(--transition),
      box-shadow var(--transition);

    &:hover:not(:disabled) {
      border-color: var(--brand);
      background-color: var(--brand-soft);
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
      opacity: 0.55;
    }
  }

  .option-item.custom-input-item {
    border-style: dashed;
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

  .option-check {
    flex-shrink: 0;
    color: var(--brand);
    font-size: 16px;
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

  .confirm-footer {
    width: 100%;
    min-height: 32px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
  }

  .confirm-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    font-size: var(--fs-body);
    color: var(--success);

    .status-icon {
      font-size: 16px;
    }
  }

  .confirm-record {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px 14px;
    background-color: rgba(var(--mcp-success-rgb), 0.08);
    border: 1px solid rgba(var(--mcp-success-rgb), 0.3);
    border-radius: var(--r-md);

    .confirm-record-question {
      font-size: var(--fs-body);
      font-weight: 600;
      color: var(--ink-900);
    }

    .confirm-record-answer {
      font-size: var(--fs-body);
      color: var(--ink-700);
    }

    .confirm-record-meta {
      font-size: var(--fs-aux);
      color: var(--ink-400);
    }
  }

  .confirm-button {
    border-radius: var(--r-sm);
    font-weight: 500;
  }
`;
