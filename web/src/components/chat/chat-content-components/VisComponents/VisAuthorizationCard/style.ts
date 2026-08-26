import styled from 'styled-components';

export const VisAuthorizationCardWrap = styled.div`
  @keyframes authRecordIn {
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

  /* ===== Header: icon chip + title + risk pill ===== */
  .auth-header {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    margin-bottom: 2px;
  }

  .auth-icon-chip {
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
  }

  .auth-title {
    font-size: var(--fs-title);
    color: var(--ink-900);
    line-height: 24px;
    font-weight: 600;
  }

  .risk-pill {
    margin-left: auto;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: var(--fs-aux);
    font-weight: 500;
    padding: 3px 9px;
    border-radius: 999px;
    white-space: nowrap;
  }

  .risk-safe {
    color: #16a34a;
    background: rgba(22, 163, 74, 0.1);
  }

  .risk-low {
    color: #2563eb;
    background: rgba(37, 99, 235, 0.1);
  }

  .risk-medium {
    color: #d97706;
    background: rgba(217, 119, 6, 0.12);
  }

  .risk-high {
    color: #ea580c;
    background: rgba(234, 88, 12, 0.1);
  }

  .risk-critical {
    color: #dc2626;
    background: rgba(220, 38, 38, 0.1);
  }

  .risk-unknown {
    color: var(--ink-500);
    background: var(--bg-fill);
  }

  /* ===== Tool panel ===== */
  .tool-info {
    margin-top: 2px;
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 12px;
    background: var(--bg-fill);
    border: 1px solid var(--line-soft);
    border-radius: var(--r-md);
  }

  .tool-icon {
    width: 26px;
    height: 26px;
    border-radius: 8px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    color: var(--brand);
    background: var(--brand-soft);
  }

  .tool-name {
    font-weight: 600;
    font-size: var(--fs-body);
    color: var(--ink-800);
    word-break: break-all;
  }

  .risk-factors {
    margin: 8px 0 0;
    display: flex;
    align-items: flex-start;
    gap: 6px;
    flex-wrap: wrap;

    .risk-factors-icon {
      color: var(--warning);
      font-size: 13px;
      margin-top: 2px;
      flex-shrink: 0;
    }

    .risk-factor-tag {
      font-size: var(--fs-aux);
      color: var(--ink-500);
      background: var(--bg-fill);
      border: 1px solid var(--line-soft);
      padding: 2px 8px;
      border-radius: 999px;
    }
  }

  .arguments-section {
    width: 100%;
    margin: 8px 0;

    .arguments-content {
      max-height: 200px;
      overflow: auto;
      background-color: var(--bg-fill);
      padding: 12px;
      border-radius: var(--r-sm);
      font-family: var(--font-mono);
      font-size: var(--fs-aux);

      .arg-item {
        margin-bottom: 8px;

        .arg-key {
          color: var(--ink-400);
        }

        .arg-value {
          margin: 4px 0 0 16px;
          white-space: pre-wrap;
          word-break: break-all;
          color: var(--ink-700);
        }
      }
    }
  }

  .session-grant-option {
    margin: 12px 0;
  }

  /* ===== Read-only record: allow / deny ===== */
  .auth-record {
    width: 100%;
    display: flex;
    border-radius: var(--r-lg);
    overflow: hidden;
    animation: authRecordIn 0.3s var(--ease-expo) both;

    &.auth-record-allow {
      background: linear-gradient(
        180deg,
        rgba(var(--mcp-success-rgb), 0.07),
        rgba(var(--mcp-success-rgb), 0.02)
      );
      border: 1px solid rgba(var(--mcp-success-rgb), 0.28);

      .record-icon {
        color: var(--success);
      }
    }

    &.auth-record-deny {
      background: linear-gradient(
        180deg,
        rgba(239, 68, 68, 0.07),
        rgba(239, 68, 68, 0.02)
      );
      border: 1px solid rgba(239, 68, 68, 0.28);

      .record-icon {
        color: var(--danger);
      }
    }

    .record-head {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      padding: 12px 14px;

      .record-avatar {
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
        background: var(--bg-elev);
        border: 1px solid var(--line-soft);
        color: var(--ink-500);
        text-transform: uppercase;

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
      }

      .record-who {
        display: flex;
        flex-direction: column;
        line-height: 1.3;
        min-width: 0;

        .record-title {
          font-size: var(--fs-body);
          font-weight: 600;
          color: var(--ink-900);
        }

        .record-time {
          font-size: var(--fs-aux);
          color: var(--ink-400);
        }
      }

      .record-icon {
        margin-left: auto;
        flex-shrink: 0;
        font-size: 18px;
      }
    }
  }

  /* ===== Footer buttons ===== */
  .auth-footer {
    width: 100%;
    font-size: var(--fs-body);
    color: var(--ink-500);
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 2px;

    button.ant-btn {
      height: 32px;
      padding: 0 16px;
      border-radius: var(--r-md) !important;
      font-weight: 500;
    }

    button.ant-btn-primary {
      background: linear-gradient(180deg, #6366f1, #4f46e5);
      border-color: transparent;
      box-shadow: 0 1px 2px rgba(var(--brand-rgb), 0.2);
    }

    button.ant-btn-primary:not(:disabled):hover {
      background: linear-gradient(180deg, #7177f5, #5546ef);
      border-color: transparent;
    }

    button.ant-btn-default:not(:disabled):hover {
      border-color: var(--danger);
      color: var(--danger);
    }
  }

  .whitespace-normal {
    width: 100%;
  }
`;