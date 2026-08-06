"use client"
import { addApp, apiInterceptors, getAppList, getTeamMode, updateApp } from '@/client/api';
import { CreateAppParams, TeamMode } from '@/types/app';
import { useRequest } from 'ahooks';
import { App, ConfigProvider, Divider, Form, Input, Modal, Spin } from 'antd';
import classNames from 'classnames';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AgentAvatarPicker } from '@/components/common/agent-avatar-picker';
import './styles.css';

interface WorkModeSelectProps {
  disable: boolean;
  options: TeamMode[];
  value?: TeamMode;
  onChange?: (value: TeamMode) => void;
}

// 自定义team_mode选择
const WorkModeSelect: React.FC<WorkModeSelectProps> = ({ disable = false, options = [], value, onChange }) => {
  const [selected, setSelected] = useState<TeamMode>(value || ({} as TeamMode));
  const { i18n } = useTranslation();

  const returnOptionStyle = (item: TeamMode) => {
    if (disable) {
      return classNames(
        `flex items-center p-4 border rounded-lg border-[#d9d9d9]  cursor-not-allowed relative transition-all duration-500 ease-in-out`,
        {
          'bg-[rgba(0,0,0,0.04)] dark:bg-[#606264]': item.value === selected?.value,
        },
      );
    }
    return `flex items-center p-4  border dark:border-[rgba(217,217,217,0.85)] rounded-lg cursor-pointer hover:border-[#4f46e5] hover:bg-[#f5faff] dark:hover:border-[rgba(12,117,252,0.85)] dark:hover:bg-[#606264] relative transition-all duration-300 ease-in-out ${
      item.value === selected?.value
        ? 'border-[#4f46e5] bg-[#f5faff] dark:bg-[#606264] dark:border-[#4f46e5]'
        : 'border-[#d9d9d9]'
    } `;
  };
  const language = i18n.language === 'en';

  return (
    <div className='grid grid-cols-2 gap-4'>
      {options.map(item => (
        <div
          className={returnOptionStyle(item)}
          key={item.value}
          onClick={() => {
            if (disable) {
              return;
            }
            setSelected(item);
            onChange?.({ ...value, ...item });
          }}
        >
          <Image src={`/icons/app/${item.value}.png`} width={48} height={48} alt={item.value} />
          <div className='flex flex-col ml-3'>
            <span className='text-xs font-medium text-[rgba(0,0,0,0.85)] dark:text-[rgba(255,255,255,0.85)] first-line:leading-6'>
              {language ? item.name_en : item.name_cn}
            </span>
            <span className='text-xs text-[rgba(0,0,0,0.45)] dark:text-[rgba(255,255,255,0.85)]'>
              {language ? item.description_en : item.description}
            </span>
          </div>
          {item.value === selected?.value && (
            <div
              className='w-3 h-3 rounded-tr-md absolute top-[1px] right-[1px] transition-all duration-300 ease-in-out'
              style={{
                background: `linear-gradient(to right top, transparent 50%, transparent 50%, ${disable ? '#d0d0d0' : '#4f46e5'} 0)`,
              }}
            />
          )}
        </div>
      ))}
    </div>
  );
};

const CreateAppModal: React.FC<{
  open: boolean;
  onCancel: () => void;
  refresh?: (newApp?: any) => void;
  type?: 'add' | 'edit';
  skipRedirect?: boolean;
}> = ({ open, onCancel, type = 'add', refresh, skipRedirect = false }) => {
  const { notification } = App.useApp();
  const [selectedIcon, setSelectedIcon] = useState<string>('');
  const { t, i18n } = useTranslation();
  const [appInfo, setAppInfo] = useState<any>({});
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const router = useRouter();

  // 在客户端加载 localStorage 数据
  useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('new_app_info');
      if (stored) {
        setAppInfo(JSON.parse(stored));
      }
    }
  });

  // 编辑态回填当前头像
  useState(() => {
    if (type === 'edit' && appInfo?.icon) {
      setSelectedIcon(appInfo.icon);
    }
  });

  // 获取工作模式列表
  const { data, loading } = useRequest(async () => {
    const [_, res] = await apiInterceptors(getTeamMode());
    return res ?? [];
  });

  // 创建应用
  const { run: createApp, loading: createLoading } = useRequest(
    async (params: CreateAppParams) => {
      if (type === 'edit') {
        return await apiInterceptors(
          updateApp({
            app_code: appInfo?.app_code,
            language: 'zh',
            ...params,
          }),
        );
      } else {
        return await apiInterceptors(
          addApp({
            language: 'zh',
            ...params,
          }),
          notification
        );
      }
    },
    {
      manual: true,
      onSuccess: async res => {
        const [error, data] = res;
        if (!error) {
          if (type === 'edit') {
            const [, res] = await apiInterceptors(getAppList({}));
            const curApp = res?.app_list?.find(item => item.app_code === appInfo?.app_code);
            localStorage.setItem('new_app_info', JSON.stringify({ ...curApp, isEdit: true }));
            message.success(t('Update_successfully'));
            await refresh?.(curApp);
          } else {
            if (data?.app_code) {
              message.success(t('Create_successfully'));
              if (!skipRedirect) {
                router.replace(`/application/app`);
              } else {
                await refresh?.(data);
              }
            } else {
              message.error(t('Create_failure'));
              await refresh?.();
            }
          }
        } else {
          message.error(type === 'edit' ? t('Update_failure') : t('Create_failure'));
          await refresh?.();
        }
        onCancel();
      },
    },
  );

  const mode = useMemo(() => {
    return data?.filter(item => item.value === appInfo?.team_mode)?.[0];
  }, [appInfo, data]);

  if (loading) {
    return null;
  }

  

  return (
    <ConfigProvider
      theme={{
        components: {
          Button: {
            defaultBorderColor: "#d9d9d9",
          },
        },
      }}
    >
      <Modal
        className="create-app-modal-container"
        title={t("create_app")}
        width={480}
        open={open}
        onOk={async () => {
          form.validateFields().then(async (values: any) => {
            await createApp({
              app_name: values?.app_name,
              app_describe: values?.app_describe,
              team_mode: values?.team_mode?.value,
              icon: values?.icon || selectedIcon,
            });
          });
        }}
        onCancel={onCancel}
        centered={true}
      >
        <Spin spinning={createLoading}>
          <div className="flex flex-1">
             <Form
               layout="vertical"
               className="w-full"
               form={form}
               initialValues={type === 'edit' ? {
                 team_mode: mode || data?.[0],
                 app_name: appInfo?.app_name,
                 app_describe: appInfo?.app_describe,
               } : {}}
            >
              <Form.Item
                label={`${t("app_name")}：`}
                name="app_name"
                required
                rules={[{ required: true, message: t("input_app_name") }]}
              >
                <Input
                  placeholder={t("input_app_name")}
                  autoComplete="off"
                  className="h-8"
                />
              </Form.Item>
              <Form.Item
                label={`${t("Description")}：`}
                name="app_describe"
                required
                rules={[
                  {
                    required: true,
                    message: t("Please_input_the_description"),
                  },
                ]}
              >
                <Input.TextArea
                  autoComplete="off"
                  placeholder={t("Please_input_the_description")}
                  autoSize={{ minRows: 2.5 }}
                />
              </Form.Item>

              <Form.Item
                label={`${t("App_icon")}`}
                name="icon"
              >
                <AgentAvatarPicker
                  value={selectedIcon}
                  name={form.getFieldValue('app_name') || ''}
                  size={64}
                  onChange={(icon) => {
                    setSelectedIcon(icon);
                    form.setFieldValue('icon', icon);
                  }}
                />
              </Form.Item>
            </Form>
          </div>
        </Spin>
      </Modal>
    </ConfigProvider>
  );
};

export default CreateAppModal;
