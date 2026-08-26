import React, { useState, useEffect, useContext } from 'react';
import { VisConfirmCardWrap } from './style';
import {
  codeComponents,
  type MarkdownComponent,
  markdownPlugins,
} from '../../config';
import { GPTVis } from '@antv/gpt-vis';
import { Button, Divider, Input, App } from 'antd';
import { BellOutlined, CheckCircleFilled } from '@ant-design/icons';
import { ChatContentContext } from '@/contexts';
import { STORAGE_USERINFO_KEY } from '@/utils/constants';

interface QuestionOption {
  label: string;
  description?: string;
  value?: string;
  requires_input?: boolean;
  input_placeholder?: string;
  input_required?: boolean;
}

interface Question {
  question: string;
  header?: string;
  options?: QuestionOption[];
  multiple?: boolean;
}

interface VisConfirmIProps {
  data: {
    markdown?: string;
    disabled?: boolean;
    extra?: {
      confirm_type?: 'confirm' | 'select' | 'input';
      confirm_message?: string;
      options?: QuestionOption[];
      default_value?: string;
      placeholder?: string;
      approval_message_id?: string;
      questions?: Question[];
      header?: string;
      original_message_id?: string;
      multiple?: boolean;
      uid?: string;
      message_id?: string;
    };
    // Structured questions support (new)
    questions?: Question[];
    header?: string;
    request_id?: string;
    allow_custom_input?: boolean;
  };
  otherComponents?: MarkdownComponent;
  onConfirm?: (extra: unknown) => void;
}

/**
 * Build the user message with system_reminder wrapping
 */
const buildConfirmUserMessage = (
  confirmType: 'confirm' | 'select' | 'input',
  question: string,
  selectedOption: string | null,
  inputValue: string,
  options: QuestionOption[],
  hasQuestions: boolean,
  questions?: Question[],
  isCustomInputMode?: boolean,
  hasOptionInput?: boolean,
): string => {
  let questionText = question;
  let headerText = '';
  if (hasQuestions && questions && questions.length > 0) {
    const primaryQuestion = questions[0];
    questionText = primaryQuestion.question;
    headerText = primaryQuestion.header || '';
  }

  let msg = '<system_reminder>\n';
  msg += '【User Confirmation Response】\n\n';

  if (headerText) {
    msg += `**${headerText}**\n\n`;
  }

  if (questionText) {
    msg += `User has responded to the following question:\n**Question**: ${questionText}\n\n`;
  }

  if (confirmType === 'select') {
    if (isCustomInputMode && inputValue.trim()) {
      msg += `**User chose custom input**: ${inputValue.trim()}\n\n`;
    } else {
      const selectedOpt = options.find(
        (o) => o.label === selectedOption || o.value === selectedOption,
      );
      if (selectedOpt) {
        msg += `**User selected**: ${selectedOpt.label}`;
        if (selectedOpt.description) {
          msg += ` - ${selectedOpt.description}`;
        }
        msg += '\n\n';

        if (hasOptionInput && inputValue.trim()) {
          msg += `**Additional notes**: ${inputValue.trim()}\n\n`;
        }
      } else if (selectedOption) {
        msg += `**User selected**: ${selectedOption}\n\n`;
      }
    }
  } else if (confirmType === 'input') {
    msg += `**User reply**: ${inputValue.trim()}\n\n`;
  } else {
    msg += '**User confirmed**\n\n';
  }

  msg +=
    '**Important**: User has completed confirmation. Please proceed based on the user\'s selection. Do not ask the same question again.\n';
  msg += '</system_reminder>';

  return msg;
};

/**
 * Build the drsk-confirm-response display message
 */
const buildConfirmResponseDisplayMessage = (
  confirmType: 'confirm' | 'select' | 'input',
  question: string,
  selectedOption: string | null,
  inputValue: string,
  options: QuestionOption[],
  hasQuestions: boolean,
  questions?: Question[],
  isCustomInputMode?: boolean,
  hasOptionInput?: boolean,
): string => {
  const timestamp = new Date().toISOString();

  let questionText = question;
  let headerText = '';
  if (hasQuestions && questions && questions.length > 0) {
    const primaryQuestion = questions[0];
    questionText = primaryQuestion.question;
    headerText = primaryQuestion.header || '';
  }

  const responseData: Record<string, unknown> = {
    confirm_type: confirmType,
    question: questionText,
    header: headerText,
    timestamp,
  };

  if (confirmType === 'select') {
    if (isCustomInputMode) {
      responseData.input_content = inputValue.trim();
    } else {
      const selectedOpt = options.find(
        (o) => o.label === selectedOption || o.value === selectedOption,
      );
      if (selectedOpt) {
        responseData.selected_option = {
          label: selectedOpt.label,
          description: selectedOpt.description,
        };
        if (hasOptionInput && inputValue.trim()) {
          responseData.input_content = inputValue.trim();
        }
      } else if (selectedOption) {
        responseData.selected_option = { label: selectedOption };
      }
    }
  } else if (confirmType === 'input') {
    responseData.input_content = inputValue.trim();
  }

  return `\`\`\`drsk-confirm-response\n${JSON.stringify(responseData, null, 2)}\n\`\`\``;
};

interface ConfirmRecordData {
  request_id?: string;
  interaction_type?: string;
  state?: 'pending' | 'responded' | 'cancelled' | 'timed_out';
  responded_at?: string;
  actor?: { user_no?: string; nick_name?: string; avatar_url?: string };
  confirm_type?: 'select' | 'input' | 'confirm';
  question?: string | null;
  header?: string | null;
  result?: {
    choice?: string | null;
    input_content?: string | null;
    is_custom_input?: boolean;
    grant_scope?: string | null;
    grant_duration?: string | null;
  };
}

const formatTime = (ts?: string) => {
  if (!ts) return '';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
};

const getCurrentUser = () => {
  try {
    const raw = localStorage.getItem(STORAGE_USERINFO_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const VisConfirmCard: React.FC<VisConfirmIProps> = ({ data, otherComponents, onConfirm }) => {
  const { message } = App.useApp();
  const [disabled, setDisabled] = useState<boolean>(!!data.disabled);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState<string>('');
  const [optionInputValue, setOptionInputValue] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);
  const [isCustomInputMode, setIsCustomInputMode] = useState<boolean>(false);
  const [confirmRecord, setConfirmRecord] = useState<ConfirmRecordData | null>(null);
  const [statusLoaded, setStatusLoaded] = useState<boolean>(false);

  const { handleChat, appInfo, scrollRef } = useContext(ChatContentContext);

  const extra = data.extra || {};
  const requestId =
    data.request_id ||
    extra.original_message_id ||
    extra.approval_message_id ||
    extra.message_id;

  // 服务端已确认记录作为唯一事实源：一旦确认（本组件提交或历史回放），卡片即只读，
  // 不能再次交互 —— 解决"反复刷新渲染仍可重复确认"的问题。
  const isConfirmedState = disabled || !!confirmRecord;
  const interactionDisabled = isConfirmedState || (!!requestId && !statusLoaded);

  useEffect(() => {
    if (!requestId) {
      setStatusLoaded(true);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
        const res = await fetch(
          `${apiBaseUrl}/api/v1/interaction/status?request_id=${encodeURIComponent(requestId)}`,
        );
        if (res.ok) {
          const json = await res.json();
          if (!cancelled && json?.responded && json.record) {
            // 服务端为唯一事实源：以服务端记录为准（谁/何时），用于渲染"已使用"态
            setConfirmRecord(json.record);
            setDisabled(true);
          }
        }
      } catch (e) {
        console.warn('Failed to fetch confirm status:', e);
      } finally {
        if (!cancelled) setStatusLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [requestId]);

  // Support both top-level questions and extra.questions
  const questions: Question[] = data.questions || extra.questions || [];
  const hasQuestions = questions.length > 0;
  const allowCustomInput = data.allow_custom_input !== false;

  let confirmType: 'confirm' | 'select' | 'input' = 'confirm';
  let confirmMessage = '';
  let options: QuestionOption[] = [];
  let placeholder = '';

  if (hasQuestions) {
    const primaryQuestion = questions[0];
    confirmMessage = primaryQuestion.question || data.header || extra.header || 'Needs your confirmation';
    options = primaryQuestion.options || [];
    confirmType = options.length > 0 ? 'select' : 'input';
    placeholder = 'Type your reply...';
  } else {
    confirmType = extra.confirm_type || 'confirm';
    confirmMessage = extra.confirm_message || 'Please confirm';
    options = extra.options || [];
    placeholder = extra.placeholder || 'Type your reply...';
  }

  const selectedOptionData = options.find(
    (o) => o.label === selectedOption || o.value === selectedOption,
  );

  const handleConfirm = async () => {
    if (disabled) return;

    let rawValue: string | null = null;
    let selectedOpt: QuestionOption | undefined;
    let finalInputValue = '';
    const actualConfirmType = isCustomInputMode ? 'input' : confirmType;

    switch (confirmType) {
      case 'select':
        if (isCustomInputMode) {
          if (!inputValue.trim()) {
            message.warning('Please enter custom content');
            return;
          }
          rawValue = inputValue.trim();
          finalInputValue = inputValue.trim();
        } else {
          if (!selectedOption) {
            message.warning('Please select an option');
            return;
          }
          rawValue = selectedOption;
          selectedOpt = options.find(
            (o) => o.label === selectedOption || o.value === selectedOption,
          );

          if (selectedOpt?.requires_input) {
            if (selectedOpt.input_required !== false && !optionInputValue.trim()) {
              message.warning('Please provide additional information');
              return;
            }
            finalInputValue = optionInputValue.trim();
          }
        }
        break;

      case 'input':
        if (!inputValue.trim()) {
          message.warning('Please enter content');
          return;
        }
        rawValue = inputValue.trim();
        finalInputValue = inputValue.trim();
        break;

      case 'confirm':
        rawValue = 'confirmed';
        break;
    }

    const userMessage = buildConfirmUserMessage(
      confirmType,
      confirmMessage,
      selectedOption,
      finalInputValue || inputValue,
      options,
      hasQuestions,
      questions,
      isCustomInputMode,
      selectedOpt?.requires_input,
    );

    setSubmitting(true);

    const user = getCurrentUser();
    const responder = {
      user_no: user?.user_no || '',
      nick_name: user?.nick_name || '',
      avatar_url: user?.avatar_url || '',
    };
    const recordHeader = hasQuestions
      ? questions[0]?.header || ''
      : data.header || extra.header || '';
    const localRecord: ConfirmRecordData = {
      request_id: requestId,
      interaction_type: actualConfirmType,
      state: 'responded',
      responded_at: new Date().toISOString(),
      actor: responder,
      confirm_type: actualConfirmType,
      question: confirmMessage,
      header: recordHeader,
      result: {
        choice: isCustomInputMode ? null : selectedOpt?.label || selectedOption,
        input_content: finalInputValue || inputValue || undefined,
        is_custom_input: isCustomInputMode,
      },
    };

    try {
      // Submit to interaction API to unblock agent; server persists who/when and
      // rejects duplicates (409) so the card can never be re-confirmed.
      if (requestId) {
        try {
          const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
          const res = await fetch(`${apiBaseUrl}/api/v1/interaction/respond`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              request_id: requestId,
              choice: selectedOption || undefined,
              input_value: finalInputValue || inputValue || undefined,
              user_message: userMessage,
              metadata: {
                confirm_type: actualConfirmType,
                is_custom_input: isCustomInputMode,
                question: confirmMessage,
                header: recordHeader,
                responder,
              },
            }),
          });

          if (res.status === 409) {
            const json = await res.json().catch(() => null);
            if (json?.record) setConfirmRecord(json.record);
            setDisabled(true);
            message.info('This confirmation has already been submitted.');
            return;
          }
          if (!res.ok) {
            console.warn('Interaction API responded with non-OK status:', res.status);
          }
        } catch (interactionError) {
          console.warn('Interaction API call failed (non-critical):', interactionError);
        }
      }

      if (handleChat) {
        await handleChat(userMessage, {
          app_code: appInfo?.app_code || '',
          original_message_id:
            data.request_id || extra.original_message_id || extra.approval_message_id || extra.message_id,
          display_metadata: {
            confirm_type: actualConfirmType,
            question: confirmMessage,
            selected_option: selectedOpt,
            input_content: finalInputValue || undefined,
            is_custom_input: isCustomInputMode,
            timestamp: new Date().toISOString(),
          },
        });
        message.success('Submitted, continuing execution...');

        setTimeout(() => {
          scrollRef?.current?.scrollTo({
            top: scrollRef.current?.scrollHeight,
            behavior: 'smooth',
          });
        }, 100);
      } else {
        // Fallback: use legacy onConfirm
        onConfirm?.(data?.extra ?? {});
        message.info('Selection recorded');
      }

      setConfirmRecord(localRecord);
      setDisabled(true);
    } catch (error) {
      console.error('Failed to submit response:', error);
      message.error('Submit failed, please try again');
    } finally {
      setSubmitting(false);
    }
  };

  const renderConfirmedRecord = () => {
    const rec = confirmRecord;
    const answer = rec?.result?.is_custom_input
      ? rec?.result?.input_content
      : rec?.result?.choice || selectedOptionData?.label || selectedOption || '';
    const who = rec?.actor?.nick_name || '';
    const avatar = rec?.actor?.avatar_url;
    const initial = (who.trim().charAt(0) || 'U').toUpperCase();

    return (
      <div className="confirm-record">
        <div className="confirm-record-head">
          <span className="confirm-record-avatar">
            {avatar ? (
              <img src={avatar} alt={who} />
            ) : (
              <span>{initial}</span>
            )}
          </span>
          <div className="confirm-record-who">
            <span className="confirm-record-title">Confirmed by {who || 'user'}</span>
            {rec?.responded_at && (
              <span className="confirm-record-time">{formatTime(rec.responded_at)}</span>
            )}
          </div>
          <CheckCircleFilled className="confirm-record-check" />
        </div>
        <div className="confirm-record-body">
          {confirmMessage && (
            <div className="confirm-record-question">{confirmMessage}</div>
          )}
          {answer && <div className="confirm-record-answer">{answer}</div>}
        </div>
      </div>
    );
  };

  const renderSelectOptions = () => {
    if (options.length === 0) return null;

    return (
      <div className="option-section">
        <div className="confirm-question">
          {hasQuestions ? confirmMessage : 'Please select:'}
        </div>
        <div className="option-list">
          {options.map((opt, idx) => {
            const optValue = opt.value || opt.label;
            const isSelected = selectedOption === optValue;
            const shouldShowInput = isSelected && opt.requires_input;

            return (
              <div key={idx} style={{ width: '100%' }}>
                <button
                  type="button"
                  className={`option-item${isSelected ? ' is-selected' : ''}`}
                  onClick={() => {
                    setSelectedOption(optValue);
                    setIsCustomInputMode(false);
                    setOptionInputValue('');
                  }}
                  disabled={interactionDisabled}
                >
                  <span className="option-radio">
                    {isSelected && <CheckCircleFilled />}
                  </span>
                  <span className="option-label-wrap">
                    <span className="option-label">{opt.label}</span>
                    {opt.description && (
                      <span className="option-desc">{opt.description}</span>
                    )}
                    {opt.requires_input && (
                      <span className="option-hint">(can add notes)</span>
                    )}
                  </span>
                </button>

                {shouldShowInput && (
                  <div className="option-input">
                    <Input.TextArea
                      value={optionInputValue}
                      onChange={(e) => setOptionInputValue(e.target.value)}
                      placeholder={opt.input_placeholder || 'Please provide additional details...'}
                      disabled={interactionDisabled}
                      rows={2}
                      autoSize={{ minRows: 2, maxRows: 4 }}
                    />
                  </div>
                )}
              </div>
            );
          })}
          {allowCustomInput && (
            <button
              type="button"
              className={`option-item custom-input-item${isCustomInputMode ? ' is-selected' : ''}`}
              onClick={() => {
                setIsCustomInputMode(true);
                setSelectedOption(null);
                setOptionInputValue('');
              }}
              disabled={interactionDisabled}
            >
              <span className="option-radio">
                {isCustomInputMode && <CheckCircleFilled />}
              </span>
              <span className="option-label-wrap">
                <span className="option-label">Custom input</span>
                <span className="option-desc">Type your own response</span>
              </span>
            </button>
          )}
        </div>
        {isCustomInputMode && (
          <div className="custom-input-area">
            <Input.TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your custom content..."
              disabled={interactionDisabled}
              rows={2}
              autoSize={{ minRows: 2, maxRows: 5 }}
            />
          </div>
        )}
      </div>
    );
  };

  const renderInput = () => {
    return (
      <div className="option-section">
        <div className="confirm-question">
          {hasQuestions ? confirmMessage : 'Please enter:'}
        </div>
        <Input.TextArea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={placeholder}
          disabled={interactionDisabled}
          rows={3}
          autoSize={{ minRows: 3, maxRows: 6 }}
        />
      </div>
    );
  };

  const renderConfirmButton = () => {
    if (isConfirmedState) {
      return (
        <div className="confirm-status">
          <span className="confirm-status-dot">
            <CheckCircleFilled />
          </span>
          <span className="confirm-status-text">Confirmed</span>
        </div>
      );
    }

    let buttonText = 'Confirm';
    let isDisabled = false;

    if (confirmType === 'select') {
      if (isCustomInputMode) {
        buttonText = 'Submit Reply';
        isDisabled = !inputValue.trim();
      } else if (selectedOptionData?.requires_input) {
        buttonText = 'Confirm Selection';
        isDisabled = selectedOptionData.input_required !== false && !optionInputValue.trim();
      } else {
        buttonText = 'Confirm Selection';
        isDisabled = !selectedOption;
      }
    } else if (confirmType === 'input') {
      buttonText = 'Submit Reply';
      isDisabled = !inputValue.trim();
    }

    return (
      <Button
        type="primary"
        className="confirm-button"
        loading={submitting}
        disabled={isDisabled || !statusLoaded}
        onClick={handleConfirm}
      >
        {buttonText}
      </Button>
    );
  };

  const cardTitle = hasQuestions ? 'Needs your confirmation' : 'Confirm Action';

  return (
    <VisConfirmCardWrap className="VisConfirmCardClass">
      <div className="card-content">
        <div className="confirm-header">
          <span className={`confirm-header-icon${isConfirmedState ? ' is-confirmed' : ''}`}>
            {isConfirmedState ? <CheckCircleFilled /> : <BellOutlined />}
          </span>
          <span className="confirm-title">{cardTitle}</span>
          {!isConfirmedState && (
            <span className="confirm-pill">Awaiting your input</span>
          )}
        </div>
        <Divider
          style={{
            margin: '12px 0',
            borderWidth: '1px',
            borderColor: 'var(--line-soft)',
          }}
        />
        <div className="confirm-markdown whitespace-normal">
          {/* @ts-ignore */}
          <GPTVis
            className="whitespace-normal"
            components={{ ...codeComponents, ...(otherComponents || {}) }}
            {...markdownPlugins}
          >
            {data?.markdown || '-'}
          </GPTVis>
        </div>

        {confirmType === 'select' && (
          isConfirmedState ? renderConfirmedRecord() : renderSelectOptions()
        )}
        {confirmType === 'input' && (
          isConfirmedState ? renderConfirmedRecord() : renderInput()
        )}
        {confirmType === 'confirm' && isConfirmedState && renderConfirmedRecord()}

        <Divider
          style={{
            margin: '12px 0',
            borderWidth: '1px',
            borderColor: 'var(--line-soft)',
          }}
        />
        <div className="confirm-footer">{renderConfirmButton()}</div>
      </div>
    </VisConfirmCardWrap>
  );
};

export default VisConfirmCard;
