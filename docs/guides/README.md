# Peiligo Guides

这里是 Peiligo(V1)的正式项目指南,面向后续接手、维护、部署这套系统的人。全部内容基于当前 `main` 分支的真实代码与文档整理;正式治理文档(ADR、评审、基线)在 [`docs/`](../README.md) 与 [`docs/adr/`](../adr/README.md),本目录不重复其内容,只做「带你上手」的整合。

## 阅读顺序

| 顺序 | 文档 | 一句话用途 |
|---|---|---|
| 1 | [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | 不懂技术也能看懂:这个系统是什么、给谁用、做完了什么、为什么这样设计 |
| 2 | [TECHNICAL_ARCHITECTURE_GUIDE.md](TECHNICAL_ARCHITECTURE_GUIDE.md) | 给工程师:技术栈、架构、数据模型、权限、生命周期、搜索、安全与生产工程 |
| 3 | [LOCAL_RUN_AND_VALIDATION_GUIDE.md](LOCAL_RUN_AND_VALIDATION_GUIDE.md) | 操作手册:本机把项目跑起来(venv 直跑 + Docker 生产同构验证),以及日常测试命令与排错 |
| 4 | [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md) | 运维交接:在一台 Linux 服务器上完成首次部署、备份恢复、监控、更新与回滚 |

## 当前项目阶段

- **Pure Development(纯开发)**:**COMPLETE(已完成)**
- **当前所处阶段**:Validation / Deployment(验证与部署)
- **Production(生产环境)**:**尚未部署**

也就是说:代码、测试、CI、Docker 生产工程、备份与监控工具都已经写完并通过本地自动化验证;但 Docker 容器实跑验证、真实服务器部署、域名/TLS、性能与无障碍正式验证、恢复演练等仍属于**待执行**事项。各文档中对每一项能力都会标注它处在哪一档:

| 标签 | 含义 |
|---|---|
| IMPLEMENTED | 代码已实现 |
| VERIFIED LOCALLY | 已被本地自动化测试 / CI 覆盖验证 |
| ENGINEERED BUT NOT YET DEPLOYED | 工程文件已就绪,但尚未在真实服务器上运行过 |
| DEPLOYMENT / VALIDATION REQUIRED | 属于部署或验证阶段必须完成的工作 |

## 相关正式文档(不在本目录)

- 运维手册:[../PRODUCTION_RUNBOOK.md](../PRODUCTION_RUNBOOK.md)
- 架构决策记录:[../adr/](../adr/README.md)(ADR-0001 ~ ADR-0006,全部 Accepted)
- 内容模型 / 信息架构:[../CONTENT_MODEL.md](../CONTENT_MODEL.md)、[../INFORMATION_ARCHITECTURE.md](../INFORMATION_ARCHITECTURE.md)
- 角色权限:[../ROLE_PERMISSION_MATRIX.md](../ROLE_PERMISSION_MATRIX.md)
- 安全基线:[../SECURITY_BASELINE.md](../SECURITY_BASELINE.md)
- 定时发布与归档:[../PUBLISH_ARCHIVE_SCHEDULING.md](../PUBLISH_ARCHIVE_SCHEDULING.md)
- 非功能需求:[../NON_FUNCTIONAL_REQUIREMENTS.md](../NON_FUNCTIONAL_REQUIREMENTS.md)
- 完工审查与签收:[../FINAL_FULL_PROJECT_REVIEW.md](../FINAL_FULL_PROJECT_REVIEW.md)、[../G2_FREEZE_EVIDENCE.md](../G2_FREEZE_EVIDENCE.md)、[../POST_G2_IMPLEMENTATION_GAP_AUDIT.md](../POST_G2_IMPLEMENTATION_GAP_AUDIT.md)
