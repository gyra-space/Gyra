from gyra._private.config import Config
from gyra_serve.agent.db.gpts_app import GptsAppDao

CFG = Config()

gpts_dao = GptsAppDao()


async def available_llms(worker_type: str = "llm"):
    types = set()

    # 数据库优先（分布式共享）：模型/LLM 配置以数据库为准，避免只读启动时加载的
    # 内存配置导致新增 provider 不生效。无记录时回退到内存配置。
    try:
        from gyra_app.config_storage.agent_llm_db_storage import (
            load_agent_llm_model_names,
        )

        db_names = load_agent_llm_model_names()
        if db_names:
            types.update(db_names)
            return list(types)
    except Exception:
        pass

    # Fetch models from global SystemApp config (proxy/provider-driven).
    if CFG.SYSTEM_APP and CFG.SYSTEM_APP.config:
        agent_llm_conf = CFG.SYSTEM_APP.config.get("agent.llm")
        if not agent_llm_conf:
            agent_conf = CFG.SYSTEM_APP.config.get("agent")
            if isinstance(agent_conf, dict):
                agent_llm_conf = agent_conf.get("llm")

        if agent_llm_conf and isinstance(agent_llm_conf.get("provider"), list):
             for p_conf in agent_llm_conf.get("provider"):
                 if isinstance(p_conf, dict) and "model" in p_conf:
                    p_models = p_conf.get("model")
                    if isinstance(p_models, list):
                        for m in p_models:
                            if isinstance(m, dict) and "name" in m:
                                types.add(m.get("name"))

        if agent_llm_conf and isinstance(agent_llm_conf.get("models"), list):
            for m in agent_llm_conf.get("models"):
                if isinstance(m, dict) and "model" in m:
                    types.add(m.get("model"))
        elif agent_llm_conf and agent_llm_conf.get("model"):
            types.add(agent_llm_conf.get("model"))

    return list(types)
