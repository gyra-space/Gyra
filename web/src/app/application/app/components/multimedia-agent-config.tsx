'use client';
import { getMultimediaAgentConfig } from '@/client/api';
import { AppContext } from '@/contexts';
import { useRequest } from 'ahooks';
import {
  App as AntApp,
  Collapse,
  Divider,
  Form,
  Input,
  InputNumber,
  Segmented,
  Select,
  Switch,
  Tooltip,
} from 'antd';
import { PictureOutlined, VideoCameraOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { useContext, useCallback, useEffect, useMemo, useState } from 'react';
import { MultimediaAgentConfig as MultimediaAgentConfigType } from '@/types/app';
import { configService, MediaModelOption } from '@/services/config';

// 图片尺寸档位：720p/1080p/2k/4k 为标准档位（后端解析为具体像素），其余为直接尺寸
const IMAGE_SIZE_OPTIONS = ['720p', '1080p', '2k', '4k', '512x512', '768x768', '1024x1024', '1024x1792', '1792x1024'];
const VIDEO_RESOLUTION_OPTIONS = ['480p', '720p', '1080p', '2k', '4k'];
const VIDEO_ASPECT_RATIO_OPTIONS = ['16:9', '9:16', '1:1', '4:3', '21:9'];

/** 「自动」占位值：空串表示使用系统默认多媒体模型（自动选择） */
const AUTO_MODEL_VALUE = '';

// 文本输入类字段统一在失焦（onBlur）时触发保存，避免输入过程中频繁请求
const TEXT_SAVE_FIELDS = ['style_prompt', 'scene_prompt', 'negative_prompt', 'file_prefix', 'fixed_params'];

export default function MultimediaAgentConfig() {
  const { appInfo, fetchUpdateApp } = useContext(AppContext);
  const { message } = AntApp.useApp();
  const [form] = Form.useForm<MultimediaAgentConfigType>();

  // 可用多媒体模型（仅多媒体生成模型，不含普通 LLM），供默认模型下拉选择
  const [imageModels, setImageModels] = useState<MediaModelOption[]>([]);
  const [videoModels, setVideoModels] = useState<MediaModelOption[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  const appCode = appInfo?.app_code || '';
  // 当前 appInfo 中已持久化的多媒体配置（ext_config.multimedia_agent）
  const persistedCfg = appInfo?.ext_config?.multimedia_agent;

  // 「可用模型」多选（候选池）：勾选后，默认模型下拉只在池内选；未勾选则用全局列表
  const watchedImageModels = Form.useWatch('image_models', form) || [];
  const watchedVideoModels = Form.useWatch('video_models', form) || [];

  // 能力类型（二选一）：决定该实例唯一允许的媒体类型，并联动展示对应配置
  const capability = Form.useWatch('capability', form) || persistedCfg?.capability || 'image';
  const isVideo = capability === 'video';

  // 默认模型下拉选项：候选池内过滤 + 「自动（系统默认）」占位
  const defaultImageOptions = useMemo(
    () => [
      { value: AUTO_MODEL_VALUE, label: '自动（系统默认）' },
      ...imageModels
        .filter((m) => (watchedImageModels.length ? watchedImageModels.includes(m.model) : true))
        .map((m) => ({ value: m.model, label: m.model })),
    ],
    [imageModels, watchedImageModels],
  );
  const defaultVideoOptions = useMemo(
    () => [
      { value: AUTO_MODEL_VALUE, label: '自动（系统默认）' },
      ...videoModels
        .filter((m) => (watchedVideoModels.length ? watchedVideoModels.includes(m.model) : true))
        .map((m) => ({ value: m.model, label: m.model })),
    ],
    [videoModels, watchedVideoModels],
  );

  useEffect(() => {
    // 多媒体模型列表来自 /api/v1/config/media-gen/available（仅多媒体模型）
    (async () => {
      setModelsLoading(true);
      try {
        const data = await configService.getAvailableMediaModels();
        setImageModels(data.image || []);
        setVideoModels(data.video || []);
      } catch (e: any) {
        message.error('加载多媒体模型列表失败: ' + (e?.message || e));
      } finally {
        setModelsLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 将已持久化配置同步到表单（fixed_params 对象转 JSON 字符串展示）
  const syncFromConfig = useCallback(
    (cfg?: MultimediaAgentConfigType) => {
      if (!cfg) return;
      form.setFieldsValue({
        ...cfg,
        capability: (cfg.capability === 'video' ? 'video' : 'image'),
        fixed_params: (cfg.fixed_params && Object.keys(cfg.fixed_params).length
          ? JSON.stringify(cfg.fixed_params, null, 2)
          : '') as unknown as Record<string, any>,
      });
    },
    [form],
  );

  // 兜底：appInfo.ext_config 尚未携带多媒体配置时，从后端读取（读 config 表，不走 app_detail）
  const { loading, run } = useRequest(
    async () => {
      if (!appCode) return;
      const res = await getMultimediaAgentConfig(appCode);
      return res?.data?.data;
    },
    {
      manual: true,
      onSuccess: (data) => {
        if (data) syncFromConfig(data);
      },
    },
  );

  // 仅在切换应用（appCode 变化）时同步一次配置，避免每次 appInfo 更新打断用户输入
  useEffect(() => {
    if (!appCode) return;
    if (persistedCfg) {
      syncFromConfig(persistedCfg);
    } else {
      run();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appCode]);

  // 统一保存：合并到 appInfo.ext_config.multimedia_agent 并走全局 fetchUpdateApp 自动保存
  const saveMultimediaCfg = useCallback(
    (values: any) => {
      const payload: any = { ...values };
      // fixed_params 表单值是 JSON 字符串，转换为对象后存储
      if (typeof payload.fixed_params === 'string') {
        try {
          payload.fixed_params = payload.fixed_params.trim()
            ? JSON.parse(payload.fixed_params)
            : {};
        } catch {
          message.warning('固定参数必须是合法的 JSON');
          return;
        }
      }
      const merged = { ...persistedCfg, ...payload };
      fetchUpdateApp({
        ...appInfo,
        ext_config: { ...(appInfo?.ext_config || {}), multimedia_agent: merged },
      });
    },
    [appInfo, persistedCfg, fetchUpdateApp, message],
  );

  // 非文本字段：任一变化即自动保存
  const onValuesChange = useCallback(
    (changedValues: any) => {
      const key = Object.keys(changedValues || {})[0];
      if (!key) return;
      // 文本输入由 onBlur 统一触发保存，避免输入过程中频繁请求
      if (TEXT_SAVE_FIELDS.includes(key)) return;
      saveMultimediaCfg(form.getFieldsValue());
    },
    [saveMultimediaCfg, form],
  );

  // 文本字段失焦时保存
  const handleTextBlur = useCallback(() => {
    saveMultimediaCfg(form.getFieldsValue());
  }, [saveMultimediaCfg, form]);

  const sectionLabel = (icon: React.ReactNode, text: string) => (
    <span className="flex items-center gap-2 text-[13px] font-medium text-gray-700">
      {icon}
      {text}
    </span>
  );

  return (
    <div className="bg-gradient-to-br from-fuchsia-50/30 to-purple-50/20 rounded-2xl border border-fuchsia-100/40 p-5 pb-3 shadow-sm">
      <Form form={form} layout="vertical" onValuesChange={onValuesChange} className="[&_.ant-form-item-label>label]:text-gray-500 [&_.ant-form-item-label>label]:!text-xs [&_.ant-form-item-label>label]:font-medium">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-fuchsia-500 to-purple-600 flex items-center justify-center shrink-0">
            <PictureOutlined className="text-white text-base" />
          </div>
          <div>
            <div className="text-[14px] font-semibold text-gray-800">多媒体 Agent 配置</div>
            <div className="text-[11px] text-gray-500">
              只使用多媒体生成模型的 Agent，可生成图片/视频（跟随上方 Agent 配置自动保存）
            </div>
          </div>
        </div>

        <Divider className="my-3" />

        {loading ? (
          <div className="py-10 text-center text-gray-400 text-xs">加载中...</div>
        ) : (
          <div className="space-y-1">
            {/* 生成能力 */}
            <Collapse
              ghost
              defaultActiveKey={['basic']}
              items={[
                {
                  key: 'basic',
                  label: sectionLabel(<VideoCameraOutlined />, '能力类型（二选一）'),
                  children: (
                    <div className="flex flex-col gap-2">
                      <Form.Item name="capability" className="mb-0">
                        <Segmented
                          block
                          options={[
                            { label: '图片 Agent', value: 'image' },
                            { label: '视频 Agent', value: 'video' },
                          ]}
                        />
                      </Form.Item>
                      <div className="text-[11px] text-gray-400">
                        一个 Agent 实例只承担一种媒体类型，运行时按此处选择生成。如需图片和视频，
                        请分别配置两个 Agent（各自选不同能力类型）。
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'model',
                  label: sectionLabel(<VideoCameraOutlined />, '可用模型 & 默认模型'),
                  children: (
                    <div className="space-y-3">
                      {isVideo ? (
                        <>
                          <Form.Item
                            name="video_models"
                            label="可用视频模型"
                            tooltip="勾选该 Agent 可以从哪些视频模型里选；留空则用系统全部可用视频模型"
                          >
                            <Select
                              mode="multiple"
                              allowClear
                              loading={modelsLoading}
                              maxTagCount="responsive"
                              placeholder="全部可用视频模型"
                              options={videoModels.map((m) => ({ value: m.model, label: m.model }))}
                              className="!rounded-xl"
                            />
                          </Form.Item>
                          <Form.Item name="default_video_model" label="默认视频模型">
                            <Select
                              allowClear
                              loading={modelsLoading}
                              options={defaultVideoOptions}
                              placeholder="自动（系统默认）"
                              className="!rounded-xl"
                            />
                          </Form.Item>
                        </>
                      ) : (
                        <>
                          <Form.Item
                            name="image_models"
                            label="可用图片模型"
                            tooltip="勾选该 Agent 可以从哪些图片模型里选；留空则用系统全部可用图片模型"
                          >
                            <Select
                              mode="multiple"
                              allowClear
                              loading={modelsLoading}
                              maxTagCount="responsive"
                              placeholder="全部可用图片模型"
                              options={imageModels.map((m) => ({ value: m.model, label: m.model }))}
                              className="!rounded-xl"
                            />
                          </Form.Item>
                          <Form.Item name="default_image_model" label="默认图片模型">
                            <Select
                              allowClear
                              loading={modelsLoading}
                              options={defaultImageOptions}
                              placeholder="自动（系统默认）"
                              className="!rounded-xl"
                            />
                          </Form.Item>
                        </>
                      )}
                    </div>
                  ),
                },
                {
                  key: 'prompt',
                  label: sectionLabel(<QuestionCircleOutlined />, '预设风格 / 场景 Prompt'),
                  children: (
                    <div className="space-y-2">
                      <Form.Item name="style_prompt" label="风格 Prompt（追加到任务描述前）">
                        <Input.TextArea rows={2} placeholder="如：赛博朋克风格，高对比度，电影级光影" className="rounded-xl resize-none" onBlur={handleTextBlur} />
                      </Form.Item>
                      <Form.Item name="scene_prompt" label="场景 Prompt（追加到任务描述后）">
                        <Input.TextArea rows={2} placeholder="如：居中构图，广角镜头，浅景深" className="rounded-xl resize-none" onBlur={handleTextBlur} />
                      </Form.Item>
                      <Form.Item name="negative_prompt" label="反向提示词（Negative Prompt）">
                        <Input.TextArea rows={2} placeholder="如：模糊，低质量，变形，水印" className="rounded-xl resize-none" onBlur={handleTextBlur} />
                      </Form.Item>
                    </div>
                  ),
                },
                {
                  key: 'output',
                  label: sectionLabel(<PictureOutlined />, '固定输出设置'),
                  children: isVideo ? (
                    <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                      <Form.Item name="default_video_resolution" label="默认视频分辨率">
                        <Select options={VIDEO_RESOLUTION_OPTIONS.map(v => ({ value: v, label: v }))} className="!rounded-xl" />
                      </Form.Item>
                      <Form.Item name="default_video_aspect_ratio" label="默认视频宽高比">
                        <Select options={VIDEO_ASPECT_RATIO_OPTIONS.map(v => ({ value: v, label: v }))} className="!rounded-xl" />
                      </Form.Item>
                      <Form.Item name="default_video_duration" label="默认视频时长（秒）">
                        <InputNumber min={1} max={600} className="w-full !rounded-xl" />
                      </Form.Item>
                    </div>
                  ) : (
                    <Form.Item name="default_image_size" label="默认图片尺寸">
                      <Select options={IMAGE_SIZE_OPTIONS.map(v => ({ value: v, label: v }))} className="!rounded-xl" />
                    </Form.Item>
                  ),
                },
                {
                  key: 'delivery',
                  label: sectionLabel(<PictureOutlined />, '交付方式'),
                  children: (
                    <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                      <Form.Item name="async_default" label={
                        <span className="flex items-center gap-1">
                          默认异步执行
                          <Tooltip title="开启后，任务默认提交到后台执行，完成后自动通知">
                            <QuestionCircleOutlined className="text-gray-400 text-[11px]" />
                          </Tooltip>
                        </span>
                      } valuePropName="checked" className="mb-2">
                        <Switch checkedChildren="是" unCheckedChildren="否" />
                      </Form.Item>
                      <Form.Item name="file_prefix" label="落盘文件名前缀">
                        <Input placeholder="generated_media" className="rounded-xl" onBlur={handleTextBlur} />
                      </Form.Item>
                      <Form.Item name="timeout" label="超时时间（秒）">
                        <InputNumber min={30} max={7200} className="w-full !rounded-xl" />
                      </Form.Item>
                    </div>
                  ),
                },
                {
                  key: 'fixed',
                  label: sectionLabel(<QuestionCircleOutlined />, '固定参数覆盖（fixed_params）'),
                  children: (
                    <Form.Item name="fixed_params" label="JSON 格式的固定 provider 参数">
                      <Input.TextArea rows={3} placeholder='如 {"quality": "hd", "n": 1, "generate_audio": true}' className="rounded-xl resize-none font-mono text-xs" onBlur={handleTextBlur} />
                    </Form.Item>
                  ),
                },
              ]}
            />
          </div>
        )}
      </Form>
    </div>
  );
}