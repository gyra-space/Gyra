import { POST } from '..';

// 合约只读视图（playbook 表收窄语义：deliverables/distill），供任务创建/引导卡选择合约
export const listPlaybooks = (data: any) => POST('/api/v1/serve_playbook_service/playbooks/list', data);
