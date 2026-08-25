'use client';

import { Button, Input } from 'antd';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { useMemo } from 'react';

const { TextArea } = Input;

function getPath(obj: Record<string, any>, path: string): any {
  return path.split('.').reduce((acc, key) => (acc == null ? acc : acc[key]), obj as any);
}

function setPath(obj: Record<string, any>, path: string, val: any) {
  const parts = path.split('.');
  const last = parts.pop() as string;
  const target = parts.reduce((acc, key) => {
    if (!acc[key] || typeof acc[key] !== 'object') acc[key] = {};
    return acc[key];
  }, obj);
  target[last] = val;
}

function listToText(list?: unknown): string {
  return Array.isArray(list) ? list.join(', ') : '';
}

function textToList(text: string): string[] {
  return text
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
}

function FieldRow({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>{label}</div>
      <Input size="small" value={value} placeholder={placeholder} onChange={e => onChange(e.target.value)} />
    </div>
  );
}

function ListField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value?: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>{label}</div>
      <Input
        size="small"
        value={listToText(value)}
        placeholder={placeholder ?? '多个用英文逗号分隔'}
        onChange={e => onChange(textToList(e.target.value))}
      />
    </div>
  );
}

export default function PayloadEditor({
  objType,
  value,
  onChange,
}: {
  objType: string;
  value: Record<string, any>;
  onChange: (v: Record<string, any>) => void;
}) {
  const update = (path: string, val: any) => {
    const next = { ...value };
    setPath(next, path, val);
    onChange(next);
  };

  const dimensionValues = useMemo(() => {
    const values = Array.isArray(value.values) ? value.values : [];
    return values.map((v: any) => ({ label: v?.label ?? '', codes: v?.codes ?? [] }));
  }, [value.values]);

  const setValues = (values: Array<{ label: string; codes: string[] }>) => {
    update('values', values);
  };

  const baseRows = (
    <>
      <ListField label="别名 alias" value={value.aliases} onChange={v => update('aliases', v)} />
      <ListField
        label="默认过滤 default_filters"
        value={value.default_filters}
        onChange={v => update('default_filters', v)}
        placeholder="如 status = 'active'"
      />
    </>
  );

  const renderFields = () => {
    switch (objType) {
      case 'entity':
        return (
          <>
            <FieldRow label="绑定表 binding.table" value={getPath(value, 'binding.table') ?? ''} onChange={v => update('binding.table', v)} placeholder="orders" />
            <FieldRow label="主键 binding.pk" value={getPath(value, 'binding.pk') ?? ''} onChange={v => update('binding.pk', v)} placeholder="id" />
            <FieldRow label="数据源 binding.datasource_id" value={String(getPath(value, 'binding.datasource_id') ?? '')} onChange={v => update('binding.datasource_id', v ? Number(v) : undefined)} placeholder="数据源 id" />
            {baseRows}
          </>
        );
      case 'metric':
        return (
          <>
            <FieldRow label="所属实体 entity" value={value.entity ?? ''} onChange={v => update('entity', v)} placeholder="ent.order" />
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>口径表达式 expression</div>
              <TextArea rows={2} size="small" value={value.expression ?? ''} onChange={e => update('expression', e.target.value)} placeholder="SUM(order.amount)" />
            </div>
            <FieldRow label="单位 unit" value={value.unit ?? ''} onChange={v => update('unit', v)} placeholder="元" />
            <ListField label="粒度 grain" value={value.grain} onChange={v => update('grain', v)} placeholder="如 day, region" />
            <ListField label="附加过滤 extra_filters" value={value.extra_filters} onChange={v => update('extra_filters', v)} placeholder="如 status = 'paid'" />
            <ListField label="别名 alias" value={value.aliases} onChange={v => update('aliases', v)} />
          </>
        );
      case 'dimension':
        return (
          <>
            <FieldRow label="维度列 column" value={value.column ?? ''} onChange={v => update('column', v)} placeholder="region" />
            <ListField label="别名 alias" value={value.aliases} onChange={v => update('aliases', v)} />
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>值映射 values</div>
              {dimensionValues.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                  <Input
                    size="small"
                    style={{ width: '30%' }}
                    placeholder="label"
                    value={item.label}
                    onChange={e => {
                      const next = dimensionValues.map((d, i) => (i === idx ? { ...d, label: e.target.value } : d));
                      setValues(next);
                    }}
                  />
                  <Input
                    size="small"
                    style={{ flex: 1 }}
                    placeholder="codes，逗号分隔（code1, code2）"
                    value={listToText(item.codes)}
                    onChange={e => {
                      const next = dimensionValues.map((d, i) => (i === idx ? { ...d, codes: textToList(e.target.value) } : d));
                      setValues(next);
                    }}
                  />
                  <Button
                    size="small"
                    type="text"
                    danger
                    icon={<MinusCircleOutlined />}
                    onClick={() => setValues(dimensionValues.filter((_, i) => i !== idx))}
                  />
                </div>
              ))}
              <Button
                size="small"
                type="dashed"
                icon={<PlusOutlined />}
                onClick={() => setValues([...dimensionValues, { label: '', codes: [] }])}
              >
                添加值
              </Button>
            </div>
          </>
        );
      case 'relation':
        return (
          <>
            <FieldRow label="from 端点" value={value.from ?? ''} onChange={v => update('from', v)} placeholder="ent.order" />
            <FieldRow label="to 端点" value={value.to ?? ''} onChange={v => update('to', v)} placeholder="ent.customer" />
            <FieldRow label="基数 cardinality" value={value.cardinality ?? ''} onChange={v => update('cardinality', v)} placeholder="many_to_one" />
            <FieldRow label="join 路径 path" value={value.path ?? ''} onChange={v => update('path', v)} placeholder="order.customer_id = customer.id" />
          </>
        );
      case 'claim':
        return (
          <>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>陈述文本 text</div>
              <TextArea rows={2} size="small" value={value.text ?? ''} onChange={e => update('text', e.target.value)} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>出处原文 source_quote</div>
              <TextArea rows={2} size="small" value={value.source_quote ?? ''} onChange={e => update('source_quote', e.target.value)} />
            </div>
            <FieldRow label="文档 ID binding.doc_id" value={getPath(value, 'binding.doc_id') ?? ''} onChange={v => update('binding.doc_id', v)} />
            <FieldRow label="空间 binding.space" value={getPath(value, 'binding.space') ?? ''} onChange={v => update('binding.space', v)} />
          </>
        );
      case 'terminology':
        return (
          <>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>定义 definition</div>
              <TextArea rows={2} size="small" value={value.definition ?? ''} onChange={e => update('definition', e.target.value)} />
            </div>
            <FieldRow label="文档 ID binding.doc_id" value={getPath(value, 'binding.doc_id') ?? ''} onChange={v => update('binding.doc_id', v)} />
            <FieldRow label="空间 binding.space" value={getPath(value, 'binding.space') ?? ''} onChange={v => update('binding.space', v)} />
            <ListField label="别名 alias" value={value.aliases} onChange={v => update('aliases', v)} />
          </>
        );
      case 'policy':
        return (
          <>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>规则 rule</div>
              <TextArea rows={2} size="small" value={value.rule ?? ''} onChange={e => update('rule', e.target.value)} />
            </div>
            <FieldRow label="条件 condition" value={value.condition ?? ''} onChange={v => update('condition', v)} />
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>出处原文 source_quote</div>
              <TextArea rows={2} size="small" value={value.source_quote ?? ''} onChange={e => update('source_quote', e.target.value)} />
            </div>
            <FieldRow label="文档 ID binding.doc_id" value={getPath(value, 'binding.doc_id') ?? ''} onChange={v => update('binding.doc_id', v)} />
            <FieldRow label="空间 binding.space" value={getPath(value, 'binding.space') ?? ''} onChange={v => update('binding.space', v)} />
          </>
        );
      default:
        return null;
    }
  };

  return <div>{renderFields()}</div>;
}
