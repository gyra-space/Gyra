import styled from 'styled-components';

export const VisConfirmCardWrap = styled.div`
  @keyframes confirmOptionIn {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  width: 100%;
  min-width: 100px;
  padding: 4px 0;

  .card-content {
    width: 100%;
    min-width: 100px;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    background: var(--bg-elev);
    border: 1px solid var(--line-soft);
    border-radius: var(--r-md);
    box-shadow: var(--sh-card);
    padding: 10px 12px;
    transition: border-color var(--transition), box-shadow var(--transition);
  }

  /* 待处理态:左侧品牌色指示条,一眼识别「需要我操作」 */
  &:not(.is-confirmed) .card-content {
    border-left: 3px solid var(--brand);
  }

  &.is-confirmed .card-content {
    border-left: 3px solid rgba(var(--mcp-success-rgb), 0.55);
  }

  /* ===== Header:标题 + 状态 pill(去掉图标徽章与分割线,更克制) ===== */
  .confirm-header {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    margin-bottom: 6px;
  }

  .confirm-header-main {
    display: flex;
    flex-direction: column;
    gap: 0;
    min-width: 0;
  }

  .confirm-title {
    font-size: var(--fs-body);
    color: var(--ink-900);
    line-height: 1.4;
    font-weight: 600;
    letter-spacing: 0.01em;
  }

  .confirm-subtitle {
    font-size: var(--fs-caption);
    color: var(--ink-400);
    line-height: 1.4;
  }

  .confirm-pill {
    margin-left: auto;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: var(--fs-caption);
    font-weight: 500;
    color: var(--brand);
    background: var(--brand-soft);
    border: 1px solid rgba(var(--brand-rgb), 0.16);
    padding: 2px 8px;
    border-radius: 999px;
    white-space: nowrap;
    line-height: 1.4;

    .anticon {
      font-size: 11px;
    }
  }

  .confirm-markdown {
    width: 100%;
    font-size: var(--fs-caption);
    color: var(--ink-700);
    line-height: 1.5;
    max-height: 96px;
    overflow-y: auto;
    padding-right: 2px;
    -webkit-overflow-scrolling: touch;

    &:empty {
      display: none;
    }
  }

  .option-section {
    width: 100%;
    margin-top: 8px;
  }

  .confirm-question {
    width: 100%;
    font-size: var(--fs-body);
    font-weight: 600;
    color: var(--ink-900);
    line-height: 1.45;
    margin-bottom: 8px;
  }

  /* ===== 选项列表:卡片式单选,左侧选中圆点 + 右侧对勾 ===== */
  .option-list {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .option-row {
    width: 100%;
    display: flex;
    flex-direction: column;
  }

  .option-item {
    position: relative;
    width: 100%;
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 7px 10px;
    text-align: left;
    font-size: var(--fs-body);
    line-height: 1.4;
    color: var(--ink-700);
    background: var(--bg-elev);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    cursor: pointer;
    animation: confirmOptionIn 0.26s var(--ease-expo) both;
    transition:
      border-color var(--transition),
      background-color var(--transition),
      box-shadow var(--transition),
      transform var(--transition);

    &:hover:not(:disabled) {
      border-color: rgba(var(--brand-rgb), 0.55);
      background: var(--brand-soft);
      transform: translateY(-1px);
      box-shadow: var(--sh-glow);
    }

    &:focus-visible {
      outline: 2px solid var(--brand);
      outline-offset: 2px;
    }

    &.is-selected {
      border-color: var(--brand);
      background: var(--brand-soft);
      color: var(--ink-900);
      box-shadow: inset 0 0 0 1px var(--brand);

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
    border-color: var(--line);

    &:hover:not(:disabled),
    &.is-selected {
      border-style: solid;
    }
  }

  /* 单选圆点:空心圈,选中时内填品牌色圆点(替代原本突兀的大对勾) */
  .option-radio {
    flex-shrink: 0;
    width: 15px;
    height: 15px;
    border-radius: 999px;
    border: 1.5px solid var(--ink-300);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: border-color var(--transition);
  }

  .option-radio-dot {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: var(--brand);
    transform: scale(0);
    transition: transform 0.18s var(--ease-expo);
  }

  .option-item.is-selected .option-radio {
    border-color: var(--brand);
  }

  .option-item.is-selected .option-radio-dot {
    transform: scale(1);
  }

  /* 自定义回复项左侧用铅笔图标替代圆点,语义更准 */
  .option-custom-icon {
    flex-shrink: 0;
    width: 15px;
    height: 15px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    color: var(--ink-400);
    transition: color var(--transition);
  }

  .option-item.is-selected .option-custom-icon {
    color: var(--brand);
  }

  /* 选中对勾:右侧收尾,默认隐藏,选中淡入 */
  .option-check {
    margin-left: auto;
    flex-shrink: 0;
    margin-top: 1px;
    font-size: 15px;
    color: var(--brand);
    opacity: 0;
    transform: scale(0.6);
    transition:
      opacity 0.18s var(--ease-expo),
      transform 0.18s var(--ease-expo);
  }

  .option-item.is-selected .option-check {
    opacity: 1;
    transform: scale(1);
  }

  .option-label-wrap {
    display: flex;
    flex-direction: column;
    gap: 0;
    min-width: 0;
    flex: 1;
  }

  .option-label {
    font-weight: 600;
    color: var(--ink-800);
  }

  .option-desc {
    font-size: var(--fs-caption);
    color: var(--ink-400);
    line-height: 1.4;
  }

  .option-hint {
    font-size: var(--fs-caption);
    color: var(--brand);
  }

  /* 选中项下方展开的补充输入区,与选项卡片视觉成组 */
  .option-input {
    margin: 4px 0 0 24px;
    animation: confirmOptionIn 0.22s var(--ease-expo) both;

    .ant-input {
      font-size: var(--fs-body);
      border-radius: var(--r-sm);
    }
  }

  /* ===== 已确认记录:分层、可信赖的收尾态 ===== */
  .confirm-record {
    width: 100%;
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(var(--mcp-success-rgb), 0.28);
    border-radius: var(--r-md);
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
      gap: 8px;
      padding: 8px 10px;
      border-bottom: 1px solid rgba(var(--mcp-success-rgb), 0.14);

      .confirm-record-avatar {
      width: 24px;
      height: 24px;
      border-radius: 999px;
      flex-shrink: 0;
      overflow: hidden;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
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
      gap: 4px;
      padding: 6px 10px 8px;

      .confirm-record-question {
        font-size: var(--fs-caption);
        color: var(--ink-500);
      }

      .confirm-record-answer {
        font-size: var(--fs-body);
        font-weight: 600;
        color: var(--ink-900);
        background: var(--bg-elev);
        border: 1px solid var(--line-soft);
        border-radius: var(--r-sm);
        padding: 5px 8px;
      }
    }
  }

  /* ===== Footer:无边框分隔,呼吸感留白 + 主按钮 ===== */
  .confirm-footer {
    width: 100%;
    min-height: 32px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    margin-top: 10px;
  }

  .confirm-button {
    height: 30px;
    padding: 0 14px;
    border-radius: var(--r-sm) !important;
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
