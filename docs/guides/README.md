# Peiligo 指南索引

这里是 Peiligo(V1)的正式项目指南目录。全部内容基于当前 `main` 分支的真实代码与文档整理;正式治理文档(ADR、评审、基线)在 [`docs/`](../) 与 [`docs/adr/`](../adr/README.md),本目录不重复其内容,只做「带你上手」的整合。

**请按你的身份选择入口,不必通读全部文档:**

---

## 第一次了解项目

想快速知道「这是什么、给谁用、做完了什么」:

| 文档 | 一句话用途 |
|---|---|
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | 项目全景:系统是什么、给谁用、做了什么、当前进展、为什么这样设计 |

读完仍想深入实现思路,再进「技术人员」一栏;只想日常用,直接看「各部门工作人员」一栏即可。

## 各部门工作人员

> **本栏内容是为零技术背景的同事写的,不需要阅读任何技术文档。**
> 你只需要一个浏览器和一个账号。

| 文档 | 一句话用途 |
|---|---|
| [DEPARTMENT_EDITOR_GUIDE.md](DEPARTMENT_EDITOR_GUIDE.md) | 部门编辑操作手册:登录网站后台、新建内容、插入图片、发布、修改、下线,附常见问题与发布前检查表 |
| [CONTENT_PUBLISHING_GUIDE.md](CONTENT_PUBLISHING_GUIDE.md) | 内容发布指南:业务流程视角——什么内容适合发、发到哪个板块、选哪种内容类型、发布前后要做什么 |

建议顺序:先读《内容发布指南》理解「发什么、发到哪」,再照《部门编辑操作手册》动手操作。

## 网站运营人员

负责内容审核、板块运营等日常工作(首页轮播、首页推荐位与紧急提示均由总管理员统一维护,需要时联系;会操作网站后台,但不写代码):

| 文档 | 一句话用途 |
|---|---|
| [CONTENT_PUBLISHING_GUIDE.md](CONTENT_PUBLISHING_GUIDE.md) | 五大板块定位、「我应该发到哪里」速查表、内容生命周期、质量检查表 |
| [DEPARTMENT_EDITOR_GUIDE.md](DEPARTMENT_EDITOR_GUIDE.md) | 后台每一步操作、每一类内容的逐字段填写说明、常见问题排查 |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | 理解系统整体能力与边界(可选,无技术门槛) |

## 技术人员

接手开发、本地运行、部署与维护:

| 顺序 | 文档 | 一句话用途 |
|---|---|---|
| 1 | [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | 全景:目标、板块、模型、权限、生命周期、当前状态 |
| 2 | [TECHNICAL_ARCHITECTURE_GUIDE.md](TECHNICAL_ARCHITECTURE_GUIDE.md) | 技术栈、架构、数据模型、权限实现、搜索、安全与生产工程 |
| 3 | [LOCAL_RUN_AND_VALIDATION_GUIDE.md](LOCAL_RUN_AND_VALIDATION_GUIDE.md) | 本机把项目跑起来(venv 直跑 + Docker 生产同构验证),测试命令与排错 |
| 4 | [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md) | 在一台 Linux 服务器上完成首次部署、备份恢复、监控、更新与回滚 |
| — | [../PRODUCTION_RUNBOOK.md](../PRODUCTION_RUNBOOK.md) | 生产运行手册(首次部署操作卡、备份、监控、恢复演练) |

## 当前项目阶段

- **Pure Development(纯开发)**:**COMPLETE(已完成)**
- **本地 Production-like Docker 运行时验证**:**PASS(2026-09-02)**,证据见 [../reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md](../reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md)
- **发布安全审查(Phase 9 Release Security Gate)**:**PASS(2026-09-12)**,安全加固(公开页 CSP、HSTS、Secure Cookie、登录防爆破、Wagtail 7.4.3 升级)已合并 main @ `725f6d1`
- **Production(生产环境)**:**尚未部署**

也就是说:代码、测试、CI、Docker 生产工程、备份与监控工具都已写完,且 Docker 容器已在本地完整实跑验证通过;但真实服务器部署、域名/TLS、生产密钥、备份独立存储、性能与无障碍正式验证、生产告警接线、恢复演练等仍属于**待执行**事项。各技术文档中对每一项能力都会标注它处在哪一档:

| 标签 | 含义 |
|---|---|
| IMPLEMENTED | 代码已实现 |
| VERIFIED LOCALLY | 已被本地自动化测试 / CI / 本地 Docker 实跑覆盖验证 |
| ENGINEERED BUT NOT YET DEPLOYED | 工程文件已就绪,但尚未在真实服务器上运行过 |
| DEPLOYMENT / VALIDATION REQUIRED | 属于部署或验证阶段必须完成的工作 |

## 相关正式文档(不在本目录)

- 运维手册:[../PRODUCTION_RUNBOOK.md](../PRODUCTION_RUNBOOK.md)
- 架构决策记录:[../adr/](../adr/README.md)(ADR-0001 ~ ADR-0007,全部 Accepted)
- 内容模型 / 信息架构:[../CONTENT_MODEL.md](../CONTENT_MODEL.md)、[../INFORMATION_ARCHITECTURE.md](../INFORMATION_ARCHITECTURE.md)
- 角色权限:[../ROLE_PERMISSION_MATRIX.md](../ROLE_PERMISSION_MATRIX.md)
- 安全基线:[../SECURITY_BASELINE.md](../SECURITY_BASELINE.md)
- 定时发布与归档:[../PUBLISH_ARCHIVE_SCHEDULING.md](../PUBLISH_ARCHIVE_SCHEDULING.md)
- 非功能需求:[../NON_FUNCTIONAL_REQUIREMENTS.md](../NON_FUNCTIONAL_REQUIREMENTS.md)
- 本地 Docker 验证证据:[../reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md](../reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md)
- 完工审查与签收:[../FINAL_FULL_PROJECT_REVIEW.md](../FINAL_FULL_PROJECT_REVIEW.md)、[../G2_FREEZE_EVIDENCE.md](../G2_FREEZE_EVIDENCE.md)、[../POST_G2_IMPLEMENTATION_GAP_AUDIT.md](../POST_G2_IMPLEMENTATION_GAP_AUDIT.md)
