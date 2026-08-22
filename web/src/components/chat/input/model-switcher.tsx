import { ChatContentContext, ChatContext } from '@/contexts';
import { SettingOutlined } from '@ant-design/icons';
import { Select, Tooltip } from 'antd';
import React, { memo, useContext, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import ModelIcon from '../content/model-icon';
import { getMultimediaConfig, isMultimediaApp } from './media-params';

const ModelSwitcher: React.FC = () => {
  const { modelList } = useContext(ChatContext);
  const { appInfo, modelValue, setModelValue, chatInParams, setChatInParams } = useContext(ChatContentContext);
  const { t } = useTranslation();

  const extendedChatInParams = useMemo(() => {
    return chatInParams?.filter(i => i.param_type !== 'model') || [];
  }, [chatInParams]);

  const model = useMemo(
    () => appInfo?.layout?.chat_in_layout?.find(i => i.param_type === 'model'),
    [appInfo?.layout?.chat_in_layout],
  );

  // 左边工具栏动态可用key
  const paramKey: string[] = useMemo(() => {
    return appInfo?.layout?.chat_in_layout?.map(i => i.param_type) || [];
  }, [appInfo?.layout?.chat_in_layout]);

  // 多媒体 Agent：模型选择器显示其配置的多媒体生成模型（而非普通 LLM 模型）
  const isMultimedia = useMemo(() => isMultimediaApp(appInfo), [appInfo]);
  const multimediaConfig = useMemo(() => getMultimediaConfig(appInfo), [appInfo]);
  const mediaModelPool = useMemo(
    () =>
      isMultimedia && multimediaConfig
        ? multimediaConfig.capability === 'video'
          ? multimediaConfig.video_models || []
          : multimediaConfig.image_models || []
        : [],
    [isMultimedia, multimediaConfig],
  );
  const defaultMediaModel = useMemo(
    () =>
      isMultimedia && multimediaConfig
        ? multimediaConfig.capability === 'video'
          ? multimediaConfig.default_video_model
          : multimediaConfig.default_image_model
        : '',
    [isMultimedia, multimediaConfig],
  );

  if (!paramKey.includes('model')) {
    return (
      <Tooltip title={t('model_tip')}>
        <div className='flex w-8 h-8 items-center justify-center rounded-md hover:bg-[rgb(221,221,221,0.6)]'>
          <SettingOutlined className='text-xl cursor-not-allowed opacity-30' />
        </div>
      </Tooltip>
    );
  }

  const handleChatInParamChange = (val: any) => {
    if (val) {
      setModelValue(val);
      const chatInParam = [
        ...extendedChatInParams,
        {
          param_type: 'model',
          param_value: val,
          sub_type: model?.sub_type,
        },
      ];
      setChatInParams(chatInParam);
    }
  };

  // 多媒体 Agent：展示多媒体模型候选池；未指定时默认模型或第一个可用，否则自动（系统默认）
  if (isMultimedia) {
    const currentMediaModel = modelValue || defaultMediaModel || mediaModelPool[0] || '';
    const options =
      mediaModelPool.length > 0
        ? mediaModelPool.map(m => ({ value: m, label: m }))
        : [{ value: currentMediaModel, label: currentMediaModel || t('media_model_auto', '自动（系统默认）') }];
    return (
      <Select
        value={currentMediaModel}
        placeholder={t('media_model_auto', '自动（系统默认）')}
        className='h-8 w-42 rounded-1xl'
        onChange={val => {
          handleChatInParamChange(val);
        }}
        popupMatchSelectWidth={300}
        options={options}
      />
    );
  }

  return (
    <Select
      value={modelValue}
      placeholder={t('choose_model')}
      className='h-8 w-42 rounded-1xl'
      onChange={val => {
        handleChatInParamChange(val);
      }}
      popupMatchSelectWidth={300}
    >
      {modelList.map(item => (
        <Select.Option key={item} >
          <div className='flex items-center'>
            <ModelIcon model={item} />
            <span className='ml-2 overflow-hidden text-ellipsis whitespace-nowrap'>{item}</span>
          </div>
        </Select.Option>
      ))}
    </Select>
  );
};

export default memo(ModelSwitcher);
