import styled from 'styled-components';

export const VisAuthorizationCardWrap = styled.div`
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

  .auth-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;

    .auth-icon {
      font-size: 18px;
      color: var(--warning);
    }

    .auth-title {
      font-size: var(--fs-title);
      color: var(--ink-900);
      line-height: 24px;
      font-weight: 600;
    }
  }

  .tool-info {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    flex-wrap: wrap;

    .tool-name {
      font-weight: 600;
      font-size: var(--fs-body);
      color: var(--ink-800);
    }
  }

  .risk-factors {
    margin: 8px 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
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

  .auth-footer {
    width: 100%;
    font-size: var(--fs-body);
    color: var(--ink-500);
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 4px;

    button {
      border-radius: var(--r-sm);
      font-weight: 500;
    }
  }

  .whitespace-normal {
    width: 100%;
  }
`;
