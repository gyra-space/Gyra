/**
 * Agent 头像上传 API。
 *
 * 复用 gyra 文件服务（multipart 上传），返回永久 `gyra-fs://` URI 作为头像值。
 * 渲染时由 `resolveAvatarUrl`/`transformFileUrl` 统一转换为可访问的图片地址，
 * 避免把带时效的签名 URL 存入 Agent 配置导致头像过期失效。
 */
import { POST } from '@/client/api';
import { IUploadFileResponse } from '@/types/flow';

/** 上传图片到 gyra 文件服务，返回 { uri, file_id, bucket, file_name } */
async function uploadToGyra(file: File): Promise<IUploadFileResponse> {
  const formData = new FormData();
  formData.append('files', file);
  const res = await POST<FormData, IUploadFileResponse[]>(
    '/api/v2/serve/file/files/gyra',
    formData,
  );
  const list = res?.data?.data;
  const first = Array.isArray(list) ? list[0] : list;
  if (!first?.uri) throw new Error('upload failed: missing uri');
  return first;
}

/**
 * 上传 Agent 头像图片，返回永久 `gyra-fs://` URI。
 * 失败时抛出异常，由调用方捕获提示。
 */
export async function uploadAgentAvatar(file: File): Promise<string> {
  const { uri } = await uploadToGyra(file);
  if (!uri) throw new Error('upload failed: missing uri');
  return uri;
}