import styled from 'styled-components';

export const VisSubagentBoardWrap = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  background-color: #fff;
  border: 1px solid #e8e8e8;
  overflow: hidden;
  margin: 4px 0;

  /* dock tab 容器内嵌：去掉卡片外壳装饰，由 tab 栏承担 header 职责 */
  &.embedded {
    border: none;
    border-radius: 0;
    margin: 0;
    background-color: transparent;
  }

  .board-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    border-bottom: 1px solid #f0f0f0;
    cursor: pointer;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .header-icon {
        font-size: 14px;
        color: #8c8c8c;
      }

      .header-title {
        font-size: 14px;
        font-weight: 500;
        color: #262626;
      }

      .header-progress {
        font-size: 13px;
        color: #8c8c8c;
      }

      .header-auth-badge {
        font-size: 12px;
        color: #f59e0b;
        background: #fffbeb;
        padding: 1px 6px;
        border-radius: 4px;
        border: 1px solid #fde68a;
      }
    }

    .header-expand {
      font-size: 12px;
      color: #bfbfbf;

      &:hover {
        color: #8c8c8c;
      }
    }
  }

  .board-items {
    display: flex;
    flex-direction: column;
    padding: 8px 0;

    .subagent-item {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 8px 12px;
      cursor: pointer;
      transition: background-color 0.15s ease;
      border-left: 3px solid transparent;

      &.running {
        background-color: #f5f3ff;
        border-left-color: #4f46e5;
      }

      &.failed {
        background-color: #fef2f2;
        border-left-color: #ef4444;
      }

      &.done {
        background-color: #f0fdf4;
        border-left-color: #52c41a;
      }

      &.awaiting_authorization {
        background-color: #fffbeb;
        border-left-color: #f59e0b;
      }

      &:hover {
        background-color: #fafafa;
      }

      .status-icon {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 1px;

        .spinner {
          width: 12px;
          height: 12px;
          border: 1.5px solid #4f46e5;
          border-top-color: transparent;
          border-radius: 50%;
          display: inline-block;
          animation: subagent-spin 0.8s linear infinite;
        }

        .dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }

        .dot.pending {
          background: #d9d9d9;
        }

        .dot.done {
          background: #52c41a;
        }

        .dot.failed {
          background: #ef4444;
        }

        .dot.awaiting {
          background: #f59e0b;
        }
      }

      .item-content {
        flex: 1;
        min-width: 0;

        .item-title-row {
          display: flex;
          align-items: center;
          gap: 6px;
          min-width: 0;
        }

        .item-title {
          font-size: 14px;
          color: #262626;
          line-height: 20px;
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;

          &.done {
            color: #8c8c8c;
          }

          &.failed {
            color: #ef4444;
            text-decoration: line-through;
          }
        }

        .item-mode {
          flex-shrink: 0;
          font-size: 11px;
          line-height: 1;
          padding: 2px 5px;
          border-radius: 4px;
          font-weight: 500;
          cursor: help;

          &.mode-async {
            color: #4f46e5;
            background: #eef2ff;
          }

          &.mode-sync {
            color: #096dd9;
            background: #e6f7ff;
          }
        }

        .item-task {
          font-size: 12px;
          color: #8c8c8c;
          line-height: 16px;
          margin-top: 2px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .item-robot {
          font-size: 13px;
          color: #4f46e5;
          flex-shrink: 0;
        }

        .item-params {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          margin-top: 4px;
          font-size: 11px;
          color: #7c3aed;
          background: #f5f3ff;
          border: 1px solid #ede9fe;
          padding: 1px 7px;
          border-radius: 6px;
          max-width: 100%;

          span {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }

        .item-auth {
          font-size: 12px;
          color: #f59e0b;
          margin-top: 2px;
        }

        .item-progress {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 6px;

          .progress-track {
            flex: 1;
            height: 4px;
            border-radius: 2px;
            background: #eef0f4;
            overflow: hidden;

            .progress-fill {
              height: 100%;
              border-radius: 2px;
              background: linear-gradient(90deg, #6366f1, #8b5cf6);
              transition: width 0.3s ease;
            }
          }

          .progress-label {
            flex-shrink: 0;
            font-size: 11px;
            color: #4f46e5;
            font-weight: 500;
          }
        }

        .item-artifacts {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 6px;

          .artifact-thumb {
            display: block;
            width: 64px;
            height: 64px;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #e8e8e8;
            background: #fafafa;
            flex-shrink: 0;

            img {
              width: 100%;
              height: 100%;
              object-fit: cover;
              display: block;
            }

            &:hover {
              border-color: #4f46e5;
            }
          }

          .artifact-link {
            font-size: 12px;
            color: #4f46e5;
            line-height: 20px;

            &:hover {
              text-decoration: underline;
            }
          }
        }

        .item-result {
          margin-top: 6px;
          font-size: 12px;

          summary {
            cursor: pointer;
            color: #6b7280;
            user-select: none;
            line-height: 18px;

            &:hover {
              color: #4f46e5;
            }
          }

          .item-result-body {
            margin-top: 4px;
            padding: 6px 8px;
            background: #f9fafb;
            border: 1px solid #f0f0f0;
            border-radius: 6px;
            color: #525252;
            line-height: 16px;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 200px;
            overflow-y: auto;
          }
        }
      }

      .item-status-badge {
        flex-shrink: 0;
        font-size: 11px;
        padding: 1px 6px;
        border-radius: 4px;
        margin-top: 1px;

        &.running {
          color: #4f46e5;
          background: #eef2ff;
        }

        &.done {
          color: #52c41a;
          background: #f0fdf4;
        }

        &.failed {
          color: #ef4444;
          background: #fef2f2;
        }

        &.pending {
          color: #8c8c8c;
          background: #f5f5f5;
        }

        &.awaiting_authorization {
          color: #f59e0b;
          background: #fffbeb;
        }
      }
    }

    .board-empty {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px 12px;
      color: #bfbfbf;
      font-size: 13px;
    }
  }

  @keyframes subagent-spin {
    to {
      transform: rotate(360deg);
    }
  }
`;
