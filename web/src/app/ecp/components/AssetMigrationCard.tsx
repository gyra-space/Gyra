'use client';

import { apiInterceptors } from '@/client/api';
import {
  exportEcpWorkspace,
  importEcpWorkspace,
  type EcpExportPayload,
} from '@/client/api/ecp';
import { DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import { App, Button, Input, Modal, Table, Upload } from 'antd';
import { useState } from 'react';

function downloadJson(data: EcpExportPayload, workspaceId: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ecp-assets-${workspaceId}-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AssetMigrationCard({ workspaceId }: { workspaceId: string }) {
  const { message } = App.useApp();
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importData, setImportData] = useState<EcpExportPayload | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});

  const doExport = async () => {
    setExporting(true);
    try {
      const [err, res] = await apiInterceptors(exportEcpWorkspace(workspaceId));
      if (err || !res) throw err ?? new Error('导出失败');
      downloadJson(res, workspaceId);
      message.success(`已导出 ${res.objects?.length ?? 0} 个语义对象`);
    } catch (e) {
      message.error(String((e as any)?.message ?? e));
    } finally {
      setExporting(false);
    }
  };

  const handleFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result as string) as EcpExportPayload;
        if (!parsed?.objects) {
          throw new Error('文件不是有效的 ECP 语义资产快照');
        }
        const initial: Record<string, string> = {};
        (parsed.datasource_refs ?? []).forEach(r => {
          initial[r.datasource_id] = r.datasource_id;
        });
        setMapping(initial);
        setImportData(parsed);
      } catch (e) {
        message.error(`解析导入文件失败: ${(e as Error)?.message ?? e}`);
      }
    };
    reader.readAsText(file);
  };

  const doImport = async () => {
    if (!importData) return;
    setImporting(true);
    try {
      const trimmedMap: Record<string, string> = {};
      for (const [k, v] of Object.entries(mapping)) {
        if (v?.trim()) trimmedMap[k] = v.trim();
      }
      const [err, res] = await apiInterceptors(
        importEcpWorkspace({
          workspace_id: workspaceId,
          data: importData,
          datasource_map: trimmedMap,
        }),
      );
      if (err || !res) throw err ?? new Error('导入失败');
      message.success(
        `已导入 ${res.imported} 个对象（跳过 ${res.skipped} 个），登记 ${res.assets_imported} 个资产引用`,
      );
      if (res.errors?.length) {
        message.warning(`导入完成，但有 ${res.errors.length} 条错误：${res.errors.slice(0, 3).join('；')}`);
      }
      setImportData(null);
      setMapping({});
    } catch (e) {
      message.error(String((e as any)?.message ?? e));
    } finally {
      setImporting(false);
    }
  };

  const dsRefs = importData?.datasource_refs ?? [];

  return (
    <div className="ecp-card" style={{ marginTop: 0 }}>
      <div className="ecp-card__title">语义资产迁移</div>
      <div style={{ fontSize: 12, color: 'var(--ink-400)', marginBottom: 12, lineHeight: 1.7 }}>
        一键导出当前语义空间的全部提案/口径资产（保留版本链与状态），可一键导入到另一个系统。
        导入时替换绑定数据源 id（datasource_id）后即可直接使用。
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <Button icon={<DownloadOutlined />} loading={exporting} onClick={doExport}>
          导出当前空间
        </Button>
        <Upload
          accept=".json"
          showUploadList={false}
          beforeUpload={file => {
            handleFile(file as File);
            return false;
          }}
        >
          <Button icon={<UploadOutlined />}>导入语义资产</Button>
        </Upload>
      </div>

      <Modal
        title="导入语义资产"
        open={!!importData}
        onCancel={() => setImportData(null)}
        onOk={doImport}
        confirmLoading={importing}
        okText="确认导入"
        cancelText="取消"
        width={720}
      >
        {dsRefs.length > 0 ? (
          <>
            <div style={{ fontSize: 12, color: 'var(--ink-400)', marginBottom: 12 }}>
              文件引用了 {dsRefs.length} 个数据源。请填写目标系统对应的
              datasource_id（旧 → 新）。留空表示沿用文件里的原值。
            </div>
            <Table
              rowKey="datasource_id"
              size="small"
              pagination={false}
              dataSource={dsRefs}
              columns={[
                {
                  title: '旧 datasource_id',
                  dataIndex: 'datasource_id',
                  width: 150,
                },
                {
                  title: '库名 / 类型',
                  width: 180,
                  render: (_, r) => (
                    <span style={{ fontSize: 12, color: 'var(--ink-500)' }}>
                      {r.db_name ?? '-'}
                      {r.db_type ? ` (${r.db_type})` : ''}
                    </span>
                  ),
                },
                {
                  title: '目标 datasource_id',
                  render: (_, r) => (
                    <Input
                      size="small"
                      value={mapping[r.datasource_id] ?? ''}
                      placeholder="新系统数据源 id"
                      onChange={e =>
                        setMapping(prev => ({
                          ...prev,
                          [r.datasource_id]: e.target.value,
                        }))
                      }
                    />
                  ),
                },
              ]}
            />
          </>
        ) : (
          <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>
            该文件未引用外部数据源，可直接导入。
          </div>
        )}
      </Modal>
    </div>
  );
}
