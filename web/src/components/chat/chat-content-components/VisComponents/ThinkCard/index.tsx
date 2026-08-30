import { DownOutlined, UpOutlined } from '@ant-design/icons';
import { Collapse } from 'antd';
import React, { useContext, useState } from 'react';
import { ThinkCardWrap } from './style';
import {
  ChatContext,
  VisCardWrapContext,
  VisMsgWrapContext,
} from '@/contexts';
import { Bubble } from '@ant-design/x';
import { markdownComponents, markdownPlugins } from '../../config';
import { GPTVis } from '@antv/gpt-vis';

interface IProps {
  data: any;
}

const ThinkCard = ({ data }: IProps) => {
  const [active, setActive] = useState<string[]>(['1']);
  const { setStepParams } = useContext(ChatContext) || {};
  const { visMsgData } = useContext(VisMsgWrapContext) || {};
  const { panelAction } = useContext(VisCardWrapContext) || {};
  
  return (
    <ThinkCardWrap style={{ background: 'transparent' }}>
      <Collapse
        defaultActiveKey={['1']}
        activeKey={active}
        ghost
        onChange={(values) => setActive(values)}
        items={[
          {
            key: '1',
            label: (
              <div
                style={{
                  display: 'inline-flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  width: '100%',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'flex-start',
                    alignItems: 'center',
                  }}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 14 14"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    style={{ display: 'inline-block' }}
                  >
                    <path
                      d="M11.8486 5.5L11.4238 5.92383L8.69727 8.65137C8.44157 8.90706 8.21562 9.13382 8.01172 9.29785C7.79912 9.46883 7.55595 9.61756 7.25 9.66602C7.08435 9.69222 6.91565 9.69222 6.75 9.66602C6.44405 9.61756 6.20088 9.46883 5.98828 9.29785C5.78438 9.13382 5.55843 8.90706 5.30273 8.65137L2.57617 5.92383L2.15137 5.5L3 4.65137L3.42383 5.07617L6.15137 7.80273C6.42595 8.07732 6.59876 8.24849 6.74023 8.3623C6.87291 8.46904 6.92272 8.47813 6.9375 8.48047C6.97895 8.48703 7.02105 8.48703 7.0625 8.48047C7.07728 8.47813 7.12709 8.46904 7.25977 8.3623C7.40124 8.24849 7.57405 8.07732 7.84863 7.80273L10.5762 5.07617L11 4.65137L11.8486 5.5Z"
                      fill="currentColor"
                    ></path>
                  </svg>
                  <span style={{ margin: '0 8px' }}>深度思考过程</span>
                  {active?.length > 0 ? <UpOutlined /> : <DownOutlined />}
                </div>
                {/* 外源 组件不展示规划详情 */}
                {/* {data?.think_link && active?.length > 0 && (
                  <div
                    style={{
                      marginLeft: 12,
                      color: '#1b62ff',
                      cursor: 'pointer',
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (panelAction) {
                        panelAction(data);
                      } else {
                        if (setStepParams) {
                          setStepParams({
                            requestUrl: data?.think_link,
                            name: '规划详情',
                            avatarUrl: visMsgData?.avatar || undefined,
                          });
                        }
                      }
                    }}
                  >
                    <img
                      src=""
                      style={{
                        display: 'inline-block',
                        width: 16,
                        height: 16,
                        margin: '0px 6px 2px 0px',
                      }}
                    />
                    <span>规划详情</span>
                  </div>
                )} */}
              </div>
            ),
            children: (
              <Bubble
                placement="start"
                messageRender={() => {
                  if (data?.markdown) {
                    return (
                      // @ts-ignore
                      <GPTVis
                        className="whitespace-normal"
                        components={markdownComponents}
                        {...markdownPlugins}
                      >
                        {data?.markdown || '-'}
                      </GPTVis>
                    );
                  }
                }}
                style={{
                  width: '100%',
                  // marginInlineEnd: 'auto',
                  borderTop: '1px solid #ccc',
                }}
                styles={{
                  content: {
                    width: '100%',
                    borderRadius: '0 16px 16px 16px',
                    minWidth: 100,
                    whiteSpace: 'pre-wrap',
                    padding: '12px 0',
                    color: '#6A7380',
                  },
                  footer: {
                    alignSelf: 'stretch',
                  },
                }}
              />
            ),
          },
        ]}
      />
    </ThinkCardWrap>
  );
};

export default ThinkCard;
