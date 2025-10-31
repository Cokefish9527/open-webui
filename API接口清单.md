# API接口清单

## ollama

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /ollama/ | GET | get_status_ollama__get | Get Status | 暂无描述 |
| /ollama/ | HEAD | get_status_ollama__head | Get Status | 暂无描述 |
| /ollama/verify | POST | verify_connection_ollama_verify_post | Verify Connection | 暂无描述 |
| /ollama/config | GET | get_config_ollama_config_get | Get Config | 暂无描述 |
| /ollama/config/update | POST | update_config_ollama_config_update_post | Update Config | 暂无描述 |
| /ollama/api/tags/{url_idx} | GET | get_ollama_tags_ollama_api_tags__url_idx__get | Get Ollama Tags | 暂无描述 |
| /ollama/api/tags | GET | get_ollama_tags_ollama_api_tags_get | Get Ollama Tags | 暂无描述 |
| /ollama/api/ps | GET | get_ollama_loaded_models_ollama_api_ps_get | Get Ollama Loaded Models | List models that are currently loaded into Ollama memory, and which node they are loaded on. |
| /ollama/api/version/{url_idx} | GET | get_ollama_versions_ollama_api_version__url_idx__get | Get Ollama Versions | 暂无描述 |
| /ollama/api/version | GET | get_ollama_versions_ollama_api_version_get | Get Ollama Versions | 暂无描述 |
| /ollama/api/unload | POST | unload_model_ollama_api_unload_post | Unload Model | 暂无描述 |
| /ollama/api/pull/{url_idx} | POST | pull_model_ollama_api_pull__url_idx__post | Pull Model | 暂无描述 |
| /ollama/api/pull | POST | pull_model_ollama_api_pull_post | Pull Model | 暂无描述 |
| /ollama/api/push/{url_idx} | DELETE | push_model_ollama_api_push__url_idx__delete | Push Model | 暂无描述 |
| /ollama/api/push | DELETE | push_model_ollama_api_push_delete | Push Model | 暂无描述 |
| /ollama/api/create/{url_idx} | POST | create_model_ollama_api_create__url_idx__post | Create Model | 暂无描述 |
| /ollama/api/create | POST | create_model_ollama_api_create_post | Create Model | 暂无描述 |
| /ollama/api/copy/{url_idx} | POST | copy_model_ollama_api_copy__url_idx__post | Copy Model | 暂无描述 |
| /ollama/api/copy | POST | copy_model_ollama_api_copy_post | Copy Model | 暂无描述 |
| /ollama/api/delete/{url_idx} | DELETE | delete_model_ollama_api_delete__url_idx__delete | Delete Model | 暂无描述 |
| /ollama/api/delete | DELETE | delete_model_ollama_api_delete_delete | Delete Model | 暂无描述 |
| /ollama/api/show | POST | show_model_info_ollama_api_show_post | Show Model Info | 暂无描述 |
| /ollama/api/embed/{url_idx} | POST | embed_ollama_api_embed__url_idx__post | Embed | 暂无描述 |
| /ollama/api/embed | POST | embed_ollama_api_embed_post | Embed | 暂无描述 |
| /ollama/api/embeddings/{url_idx} | POST | embeddings_ollama_api_embeddings__url_idx__post | Embeddings | 暂无描述 |
| /ollama/api/embeddings | POST | embeddings_ollama_api_embeddings_post | Embeddings | 暂无描述 |
| /ollama/api/generate/{url_idx} | POST | generate_completion_ollama_api_generate__url_idx__post | Generate Completion | 暂无描述 |
| /ollama/api/generate | POST | generate_completion_ollama_api_generate_post | Generate Completion | 暂无描述 |
| /ollama/api/chat/{url_idx} | POST | generate_chat_completion_ollama_api_chat__url_idx__post | Generate Chat Completion | 暂无描述 |
| /ollama/api/chat | POST | generate_chat_completion_ollama_api_chat_post | Generate Chat Completion | 暂无描述 |
| /ollama/v1/completions/{url_idx} | POST | generate_openai_completion_ollama_v1_completions__url_idx__post | Generate Openai Completion | 暂无描述 |
| /ollama/v1/completions | POST | generate_openai_completion_ollama_v1_completions_post | Generate Openai Completion | 暂无描述 |
| /ollama/v1/chat/completions/{url_idx} | POST | generate_openai_chat_completion_ollama_v1_chat_completions__url_idx__post | Generate Openai Chat Completion | 暂无描述 |
| /ollama/v1/chat/completions | POST | generate_openai_chat_completion_ollama_v1_chat_completions_post | Generate Openai Chat Completion | 暂无描述 |
| /ollama/v1/models/{url_idx} | GET | get_openai_models_ollama_v1_models__url_idx__get | Get Openai Models | 暂无描述 |
| /ollama/v1/models | GET | get_openai_models_ollama_v1_models_get | Get Openai Models | 暂无描述 |
| /ollama/models/download/{url_idx} | POST | download_model_ollama_models_download__url_idx__post | Download Model | 暂无描述 |
| /ollama/models/download | POST | download_model_ollama_models_download_post | Download Model | 暂无描述 |
| /ollama/models/upload/{url_idx} | POST | upload_model_ollama_models_upload__url_idx__post | Upload Model | 暂无描述 |
| /ollama/models/upload | POST | upload_model_ollama_models_upload_post | Upload Model | 暂无描述 |

## openai

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /openai/config | GET | get_config_openai_config_get | Get Config | 暂无描述 |
| /openai/config/update | POST | update_config_openai_config_update_post | Update Config | 暂无描述 |
| /openai/audio/speech | POST | speech_openai_audio_speech_post | Speech | 暂无描述 |
| /openai/models/{url_idx} | GET | get_models_openai_models__url_idx__get | Get Models | 暂无描述 |
| /openai/models | GET | get_models_openai_models_get | Get Models | 暂无描述 |
| /openai/verify | POST | verify_connection_openai_verify_post | Verify Connection | 暂无描述 |
| /openai/chat/completions | POST | generate_chat_completion_openai_chat_completions_post | Generate Chat Completion | 暂无描述 |
| /openai/{path} | GET | proxy_openai__path__get | Proxy | Deprecated: proxy all requests to OpenAI API |
| /openai/{path} | POST | proxy_openai__path__get | Proxy | Deprecated: proxy all requests to OpenAI API |
| /openai/{path} | DELETE | proxy_openai__path__get | Proxy | Deprecated: proxy all requests to OpenAI API |
| /openai/{path} | PUT | proxy_openai__path__get | Proxy | Deprecated: proxy all requests to OpenAI API |

## 管线管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/pipelines/list | GET | get_pipelines_list_api_v1_pipelines_list_get | Get Pipelines List | 暂无描述 |
| /api/v1/pipelines/upload | POST | upload_pipeline_api_v1_pipelines_upload_post | Upload Pipeline | 暂无描述 |
| /api/v1/pipelines/add | POST | add_pipeline_api_v1_pipelines_add_post | Add Pipeline | 暂无描述 |
| /api/v1/pipelines/delete | DELETE | delete_pipeline_api_v1_pipelines_delete_delete | Delete Pipeline | 暂无描述 |
| /api/v1/pipelines/ | GET | get_pipelines_api_v1_pipelines__get | Get Pipelines | 暂无描述 |
| /api/v1/pipelines/{pipeline_id}/valves | GET | get_pipeline_valves_api_v1_pipelines__pipeline_id__valves_get | Get Pipeline Valves | 暂无描述 |
| /api/v1/pipelines/{pipeline_id}/valves/spec | GET | get_pipeline_valves_spec_api_v1_pipelines__pipeline_id__valves_spec_get | Get Pipeline Valves Spec | 暂无描述 |
| /api/v1/pipelines/{pipeline_id}/valves/update | POST | update_pipeline_valves_api_v1_pipelines__pipeline_id__valves_update_post | Update Pipeline Valves | 暂无描述 |

## 任务管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/tasks/config | GET | get_task_config_api_v1_tasks_config_get | Get Task Config | 暂无描述 |
| /api/v1/tasks/config/update | POST | update_task_config_api_v1_tasks_config_update_post | Update Task Config | 暂无描述 |
| /api/v1/tasks/title/completions | POST | generate_title_api_v1_tasks_title_completions_post | Generate Title | 暂无描述 |
| /api/v1/tasks/follow_up/completions | POST | generate_follow_ups_api_v1_tasks_follow_up_completions_post | Generate Follow Ups | 暂无描述 |
| /api/v1/tasks/tags/completions | POST | generate_chat_tags_api_v1_tasks_tags_completions_post | Generate Chat Tags | 暂无描述 |
| /api/v1/tasks/image_prompt/completions | POST | generate_image_prompt_api_v1_tasks_image_prompt_completions_post | Generate Image Prompt | 暂无描述 |
| /api/v1/tasks/queries/completions | POST | generate_queries_api_v1_tasks_queries_completions_post | Generate Queries | 暂无描述 |
| /api/v1/tasks/auto/completions | POST | generate_autocompletion_api_v1_tasks_auto_completions_post | Generate Autocompletion | 暂无描述 |
| /api/v1/tasks/emoji/completions | POST | generate_emoji_api_v1_tasks_emoji_completions_post | Generate Emoji | 暂无描述 |
| /api/v1/tasks/moa/completions | POST | generate_moa_response_api_v1_tasks_moa_completions_post | Generate Moa Response | 暂无描述 |

## images

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/images/config | GET | get_config_api_v1_images_config_get | Get Config | 暂无描述 |
| /api/v1/images/config/update | POST | update_config_api_v1_images_config_update_post | Update Config | 暂无描述 |
| /api/v1/images/config/url/verify | GET | verify_url_api_v1_images_config_url_verify_get | Verify Url | 暂无描述 |
| /api/v1/images/image/config | GET | get_image_config_api_v1_images_image_config_get | Get Image Config | 暂无描述 |
| /api/v1/images/image/config/update | POST | update_image_config_api_v1_images_image_config_update_post | Update Image Config | 暂无描述 |
| /api/v1/images/models | GET | get_models_api_v1_images_models_get | Get Models | 暂无描述 |
| /api/v1/images/generations | POST | image_generations_api_v1_images_generations_post | Image Generations | 暂无描述 |

## audio

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/audio/config | GET | get_audio_config_api_v1_audio_config_get | Get Audio Config | 暂无描述 |
| /api/v1/audio/config/update | POST | update_audio_config_api_v1_audio_config_update_post | Update Audio Config | 暂无描述 |
| /api/v1/audio/speech | POST | speech_api_v1_audio_speech_post | Speech | 暂无描述 |
| /api/v1/audio/transcriptions | POST | transcription_api_v1_audio_transcriptions_post | Transcription | 暂无描述 |
| /api/v1/audio/models | GET | get_models_api_v1_audio_models_get | Get Models | 暂无描述 |
| /api/v1/audio/voices | GET | get_voices_api_v1_audio_voices_get | Get Voices | 暂无描述 |

## retrieval

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/retrieval/ | GET | get_status_api_v1_retrieval__get | Get Status | 暂无描述 |
| /api/v1/retrieval/embedding | GET | get_embedding_config_api_v1_retrieval_embedding_get | Get Embedding Config | 暂无描述 |
| /api/v1/retrieval/embedding/update | POST | update_embedding_config_api_v1_retrieval_embedding_update_post | Update Embedding Config | 暂无描述 |
| /api/v1/retrieval/config | GET | get_rag_config_api_v1_retrieval_config_get | Get Rag Config | 暂无描述 |
| /api/v1/retrieval/config/update | POST | update_rag_config_api_v1_retrieval_config_update_post | Update Rag Config | 暂无描述 |
| /api/v1/retrieval/process/file | POST | process_file_api_v1_retrieval_process_file_post | Process File | 暂无描述 |
| /api/v1/retrieval/process/text | POST | process_text_api_v1_retrieval_process_text_post | Process Text | 暂无描述 |
| /api/v1/retrieval/process/youtube | POST | process_youtube_video_api_v1_retrieval_process_youtube_post | Process Youtube Video | 暂无描述 |
| /api/v1/retrieval/process/web | POST | process_web_api_v1_retrieval_process_web_post | Process Web | 暂无描述 |
| /api/v1/retrieval/process/web/search | POST | process_web_search_api_v1_retrieval_process_web_search_post | Process Web Search | 暂无描述 |
| /api/v1/retrieval/query/doc | POST | query_doc_handler_api_v1_retrieval_query_doc_post | Query Doc Handler | 暂无描述 |
| /api/v1/retrieval/query/collection | POST | query_collection_handler_api_v1_retrieval_query_collection_post | Query Collection Handler | 暂无描述 |
| /api/v1/retrieval/delete | POST | delete_entries_from_collection_api_v1_retrieval_delete_post | Delete Entries From Collection | 暂无描述 |
| /api/v1/retrieval/reset/db | POST | reset_vector_db_api_v1_retrieval_reset_db_post | Reset Vector Db | 暂无描述 |
| /api/v1/retrieval/reset/uploads | POST | reset_upload_dir_api_v1_retrieval_reset_uploads_post | Reset Upload Dir | 暂无描述 |
| /api/v1/retrieval/ef/{text} | GET | get_embeddings_api_v1_retrieval_ef__text__get | Get Embeddings | 暂无描述 |
| /api/v1/retrieval/process/files/batch | POST | process_files_batch_api_v1_retrieval_process_files_batch_post | Process Files Batch | Process a batch of files and save them to the vector database. |

## 配置管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/configs/import | POST | import_config_api_v1_configs_import_post | Import Config | 暂无描述 |
| /api/v1/configs/export | GET | export_config_api_v1_configs_export_get | Export Config | 暂无描述 |
| /api/v1/configs/direct_connections | GET | get_direct_connections_config_api_v1_configs_direct_connections_get | Get Direct Connections Config | 暂无描述 |
| /api/v1/configs/direct_connections | POST | set_direct_connections_config_api_v1_configs_direct_connections_post | Set Direct Connections Config | 暂无描述 |
| /api/v1/configs/tool_servers | GET | get_tool_servers_config_api_v1_configs_tool_servers_get | Get Tool Servers Config | 暂无描述 |
| /api/v1/configs/tool_servers | POST | set_tool_servers_config_api_v1_configs_tool_servers_post | Set Tool Servers Config | 暂无描述 |
| /api/v1/configs/tool_servers/verify | POST | verify_tool_servers_config_api_v1_configs_tool_servers_verify_post | Verify Tool Servers Config | Verify the connection to the tool server. |
| /api/v1/configs/code_execution | GET | get_code_execution_config_api_v1_configs_code_execution_get | Get Code Execution Config | 暂无描述 |
| /api/v1/configs/code_execution | POST | set_code_execution_config_api_v1_configs_code_execution_post | Set Code Execution Config | 暂无描述 |
| /api/v1/configs/models | GET | get_models_config_api_v1_configs_models_get | Get Models Config | 暂无描述 |
| /api/v1/configs/models | POST | set_models_config_api_v1_configs_models_post | Set Models Config | 暂无描述 |
| /api/v1/configs/suggestions | POST | set_default_suggestions_api_v1_configs_suggestions_post | Set Default Suggestions | 暂无描述 |
| /api/v1/configs/banners | GET | get_banners_api_v1_configs_banners_get | Get Banners | 暂无描述 |
| /api/v1/configs/banners | POST | set_banners_api_v1_configs_banners_post | Set Banners | 暂无描述 |
| /api/v1/configs/usage | GET | get_usage_config_api_v1_configs_usage_get | Get Usage Config | 暂无描述 |
| /api/v1/configs/usage | POST | set_usage_config_api_v1_configs_usage_post | Set Usage Config | 暂无描述 |

## 认证与授权

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/auths/ | GET | get_session_user_api_v1_auths__get | Get Session User | 暂无描述 |
| /api/v1/auths/update/profile | POST | update_profile_api_v1_auths_update_profile_post | Update Profile | 暂无描述 |
| /api/v1/auths/update/password | POST | update_password_api_v1_auths_update_password_post | Update Password | 暂无描述 |
| /api/v1/auths/ldap | POST | ldap_auth_api_v1_auths_ldap_post | Ldap Auth | 暂无描述 |
| /api/v1/auths/signin | POST | signin_api_v1_auths_signin_post | Signin | 暂无描述 |
| /api/v1/auths/signup | POST | signup_api_v1_auths_signup_post | Signup | 暂无描述 |
| /api/v1/auths/signup_verify/{code} | GET | signup_verify_api_v1_auths_signup_verify__code__get | Signup Verify | 暂无描述 |
| /api/v1/auths/signout | GET | signout_api_v1_auths_signout_get | Signout | 暂无描述 |
| /api/v1/auths/add | POST | add_user_api_v1_auths_add_post | Add User | 暂无描述 |
| /api/v1/auths/admin/details | GET | get_admin_details_api_v1_auths_admin_details_get | Get Admin Details | 暂无描述 |
| /api/v1/auths/admin/config | GET | get_admin_config_api_v1_auths_admin_config_get | Get Admin Config | 暂无描述 |
| /api/v1/auths/admin/config | POST | update_admin_config_api_v1_auths_admin_config_post | Update Admin Config | 暂无描述 |
| /api/v1/auths/admin/config/ldap/server | GET | get_ldap_server_api_v1_auths_admin_config_ldap_server_get | Get Ldap Server | 暂无描述 |
| /api/v1/auths/admin/config/ldap/server | POST | update_ldap_server_api_v1_auths_admin_config_ldap_server_post | Update Ldap Server | 暂无描述 |
| /api/v1/auths/admin/config/ldap | GET | get_ldap_config_api_v1_auths_admin_config_ldap_get | Get Ldap Config | 暂无描述 |
| /api/v1/auths/admin/config/ldap | POST | update_ldap_config_api_v1_auths_admin_config_ldap_post | Update Ldap Config | 暂无描述 |
| /api/v1/auths/api_key | GET | get_api_key_api_v1_auths_api_key_get | Get Api Key | 暂无描述 |
| /api/v1/auths/api_key | POST | generate_api_key_api_v1_auths_api_key_post | Generate Api Key | 暂无描述 |
| /api/v1/auths/api_key | DELETE | delete_api_key_api_v1_auths_api_key_delete | Delete Api Key | 暂无描述 |

## 用户管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/users/active | GET | get_active_users_api_v1_users_active_get | Get Active Users | Get a list of active users. |
| /api/v1/users/ | GET | get_users_api_v1_users__get | Get Users | 暂无描述 |
| /api/v1/users/all | GET | get_all_users_api_v1_users_all_get | Get All Users | 暂无描述 |
| /api/v1/users/groups | GET | get_user_groups_api_v1_users_groups_get | Get User Groups | 暂无描述 |
| /api/v1/users/permissions | GET | get_user_permissisions_api_v1_users_permissions_get | Get User Permissisions | 暂无描述 |
| /api/v1/users/default/permissions | GET | get_default_user_permissions_api_v1_users_default_permissions_get | Get Default User Permissions | 暂无描述 |
| /api/v1/users/default/permissions | POST | update_default_user_permissions_api_v1_users_default_permissions_post | Update Default User Permissions | 暂无描述 |
| /api/v1/users/user/settings | GET | get_user_settings_by_session_user_api_v1_users_user_settings_get | Get User Settings By Session User | 暂无描述 |
| /api/v1/users/user/settings/update | POST | update_user_settings_by_session_user_api_v1_users_user_settings_update_post | Update User Settings By Session User | 暂无描述 |
| /api/v1/users/user/info | GET | get_user_info_by_session_user_api_v1_users_user_info_get | Get User Info By Session User | 暂无描述 |
| /api/v1/users/user/info/update | POST | update_user_info_by_session_user_api_v1_users_user_info_update_post | Update User Info By Session User | 暂无描述 |
| /api/v1/users/{user_id} | GET | get_user_by_id_api_v1_users__user_id__get | Get User By Id | 暂无描述 |
| /api/v1/users/{user_id} | DELETE | delete_user_by_id_api_v1_users__user_id__delete | Delete User By Id | 暂无描述 |
| /api/v1/users/{user_id}/active | GET | get_user_active_status_by_id_api_v1_users__user_id__active_get | Get User Active Status By Id | 暂无描述 |
| /api/v1/users/{user_id}/update | POST | update_user_by_id_api_v1_users__user_id__update_post | Update User By Id | 暂无描述 |
| /api/v1/users/{user_id}/credit | PUT | update_credit_by_user_id_api_v1_users__user_id__credit_put | Update Credit By User Id | 暂无描述 |
| /api/v1/users/user/business_name/update | POST | update_user_business_name_by_session_user_api_v1_users_user_business_name_update_post | Update User Business Name By Session User | 更新当前用户的公司名称 |

## credit

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/credit/config | GET | get_config_api_v1_credit_config_get | Get Config | 暂无描述 |
| /api/v1/credit/logs | GET | list_credit_logs_api_v1_credit_logs_get | List Credit Logs | 暂无描述 |
| /api/v1/credit/all_logs | GET | get_all_logs_api_v1_credit_all_logs_get | Get All Logs | 暂无描述 |
| /api/v1/credit/tickets | POST | create_ticket_api_v1_credit_tickets_post | Create Ticket | 暂无描述 |
| /api/v1/credit/callback | GET | ticket_callback_api_v1_credit_callback_get | Ticket Callback | 暂无描述 |
| /api/v1/credit/callback/redirect | GET | ticket_callback_redirect_api_v1_credit_callback_redirect_get | Ticket Callback Redirect | 暂无描述 |
| /api/v1/credit/models/price | GET | get_model_price_api_v1_credit_models_price_get | Get Model Price | 暂无描述 |
| /api/v1/credit/models/price | PUT | update_model_price_api_v1_credit_models_price_put | Update Model Price | 暂无描述 |
| /api/v1/credit/statistics | POST | get_statistics_api_v1_credit_statistics_post | Get Statistics | 暂无描述 |

## 计费管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/billing/billing/user/credit | GET | get_user_company_credit_api_v1_billing_billing_user_credit_get | 获取用户所属公司的积分余额 | 返回当前登录用户所属公司（若有）的积分余额信息。 |
| /api/v1/billing/billing/configs | GET | get_billing_configs_api_v1_billing_billing_configs_get | 获取计费配置列表 | 获取计费配置列表（分页）。

Args:
    config_type (Optional[str]): 配置类型过滤
    is_active (Optional[bool]): 是否启用过滤
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    user: 已认证的管理员用户对象
    
Returns:
    PaginatedBillingConfigResponse: 分页的计费配置列表 |
| /api/v1/billing/billing/configs | POST | create_billing_config_api_v1_billing_billing_configs_post | 创建计费配置 | 创建新的计费配置。

Args:
    form_data (BillingConfigForm): 计费配置创建表单
    user: 已认证的管理员用户对象
    
Returns:
    BillingConfigResponse: 创建的计费配置信息 |
| /api/v1/billing/billing/configs/{config_id} | GET | get_billing_config_api_v1_billing_billing_configs__config_id__get | 获取计费配置详情 | 获取单个计费配置详情 |
| /api/v1/billing/billing/configs/{config_id} | PUT | update_billing_config_api_v1_billing_billing_configs__config_id__put | 更新计费配置 | 更新计费配置 |
| /api/v1/billing/billing/configs/{config_id} | DELETE | delete_billing_config_api_v1_billing_billing_configs__config_id__delete | 删除计费配置 | 删除计费配置 |
| /api/v1/billing/billing/usage-logs | GET | get_api_usage_logs_api_v1_billing_billing_usage_logs_get | 获取API使用记录列表 | 获取API使用记录列表（分页）。

Args:
    user_id (Optional[str]): 用户ID过滤
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    user: 已认证的用户对象
    
Returns:
    PaginatedAPIUsageLogResponse: 分页的API使用记录列表 |
| /api/v1/billing/billing/usage-logs | POST | create_api_usage_log_api_v1_billing_billing_usage_logs_post | 创建API使用记录 | 创建新的API使用记录。

Args:
    form_data (APIUsageLogForm): API使用记录创建表单
    user: 已认证的管理员用户对象
    
Returns:
    APIUsageLogResponse: 创建的API使用记录信息 |
| /api/v1/billing/billing/usage-logs/session/{session_id} | GET | get_api_usage_logs_by_session_api_v1_billing_billing_usage_logs_session__session_id__get | 根据会话ID获取API使用记录 | 根据会话ID获取API使用记录 |
| /api/v1/billing/billing/usage-logs/session/{session_id}/total | GET | get_total_credits_consumed_by_session_api_v1_billing_billing_usage_logs_session__session_id__total_get | 根据会话ID获取总消耗积分 | 根据会话ID获取总消耗积分 |

## channels

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/channels/ | GET | get_channels_api_v1_channels__get | Get Channels | 暂无描述 |
| /api/v1/channels/create | POST | create_new_channel_api_v1_channels_create_post | Create New Channel | 暂无描述 |
| /api/v1/channels/{id} | GET | get_channel_by_id_api_v1_channels__id__get | Get Channel By Id | 暂无描述 |
| /api/v1/channels/{id}/update | POST | update_channel_by_id_api_v1_channels__id__update_post | Update Channel By Id | 暂无描述 |
| /api/v1/channels/{id}/delete | DELETE | delete_channel_by_id_api_v1_channels__id__delete_delete | Delete Channel By Id | 暂无描述 |
| /api/v1/channels/{id}/messages | GET | get_channel_messages_api_v1_channels__id__messages_get | Get Channel Messages | 暂无描述 |
| /api/v1/channels/{id}/messages/post | POST | post_new_message_api_v1_channels__id__messages_post_post | Post New Message | 暂无描述 |
| /api/v1/channels/{id}/messages/{message_id} | GET | get_channel_message_api_v1_channels__id__messages__message_id__get | Get Channel Message | 暂无描述 |
| /api/v1/channels/{id}/messages/{message_id}/thread | GET | get_channel_thread_messages_api_v1_channels__id__messages__message_id__thread_get | Get Channel Thread Messages | 暂无描述 |
| /api/v1/channels/{id}/messages/{message_id}/update | POST | update_message_by_id_api_v1_channels__id__messages__message_id__update_post | Update Message By Id | 暂无描述 |
| /api/v1/channels/{id}/messages/{message_id}/reactions/add | POST | add_reaction_to_message_api_v1_channels__id__messages__message_id__reactions_add_post | Add Reaction To Message | 暂无描述 |
| /api/v1/channels/{id}/messages/{message_id}/reactions/remove | POST | remove_reaction_by_id_and_user_id_and_name_api_v1_channels__id__messages__message_id__reactions_remove_post | Remove Reaction By Id And User Id And Name | 暂无描述 |
| /api/v1/channels/{id}/messages/{message_id}/delete | DELETE | delete_message_by_id_api_v1_channels__id__messages__message_id__delete_delete | Delete Message By Id | 暂无描述 |

## 对话管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/chats/list | GET | get_session_user_chat_list_api_v1_chats_list_get | Get Session User Chat List | 暂无描述 |
| /api/v1/chats/ | GET | get_session_user_chat_list_api_v1_chats__get | Get Session User Chat List | 暂无描述 |
| /api/v1/chats/ | DELETE | delete_all_user_chats_api_v1_chats__delete | Delete All User Chats | 暂无描述 |
| /api/v1/chats/list/user/{user_id} | GET | get_user_chat_list_by_user_id_api_v1_chats_list_user__user_id__get | Get User Chat List By User Id | 暂无描述 |
| /api/v1/chats/new | POST | create_new_chat_api_v1_chats_new_post | Create New Chat | 暂无描述 |
| /api/v1/chats/import | POST | import_chat_api_v1_chats_import_post | Import Chat | 暂无描述 |
| /api/v1/chats/search | GET | search_user_chats_api_v1_chats_search_get | Search User Chats | 暂无描述 |
| /api/v1/chats/folder/{folder_id} | GET | get_chats_by_folder_id_api_v1_chats_folder__folder_id__get | Get Chats By Folder Id | 暂无描述 |
| /api/v1/chats/pinned | GET | get_user_pinned_chats_api_v1_chats_pinned_get | Get User Pinned Chats | 暂无描述 |
| /api/v1/chats/all | GET | get_user_chats_api_v1_chats_all_get | Get User Chats | 暂无描述 |
| /api/v1/chats/all/archived | GET | get_user_archived_chats_api_v1_chats_all_archived_get | Get User Archived Chats | 暂无描述 |
| /api/v1/chats/all/tags | GET | get_all_user_tags_api_v1_chats_all_tags_get | Get All User Tags | 暂无描述 |
| /api/v1/chats/all/db | GET | get_all_user_chats_in_db_api_v1_chats_all_db_get | Get All User Chats In Db | 暂无描述 |
| /api/v1/chats/archived | GET | get_archived_session_user_chat_list_api_v1_chats_archived_get | Get Archived Session User Chat List | 暂无描述 |
| /api/v1/chats/archive/all | POST | archive_all_chats_api_v1_chats_archive_all_post | Archive All Chats | 暂无描述 |
| /api/v1/chats/share/{share_id} | GET | get_shared_chat_by_id_api_v1_chats_share__share_id__get | Get Shared Chat By Id | 暂无描述 |
| /api/v1/chats/tags | POST | get_user_chat_list_by_tag_name_api_v1_chats_tags_post | Get User Chat List By Tag Name | 暂无描述 |
| /api/v1/chats/{id} | GET | get_chat_by_id_api_v1_chats__id__get | Get Chat By Id | 暂无描述 |
| /api/v1/chats/{id} | POST | update_chat_by_id_api_v1_chats__id__post | Update Chat By Id | 暂无描述 |
| /api/v1/chats/{id} | DELETE | delete_chat_by_id_api_v1_chats__id__delete | Delete Chat By Id | 暂无描述 |
| /api/v1/chats/{id}/messages/{message_id} | POST | update_chat_message_by_id_api_v1_chats__id__messages__message_id__post | Update Chat Message By Id | 暂无描述 |
| /api/v1/chats/{id}/messages/{message_id}/event | POST | send_chat_message_event_by_id_api_v1_chats__id__messages__message_id__event_post | Send Chat Message Event By Id | 暂无描述 |
| /api/v1/chats/{id}/pinned | GET | get_pinned_status_by_id_api_v1_chats__id__pinned_get | Get Pinned Status By Id | 暂无描述 |
| /api/v1/chats/{id}/pin | POST | pin_chat_by_id_api_v1_chats__id__pin_post | Pin Chat By Id | 暂无描述 |
| /api/v1/chats/{id}/clone | POST | clone_chat_by_id_api_v1_chats__id__clone_post | Clone Chat By Id | 暂无描述 |
| /api/v1/chats/{id}/clone/shared | POST | clone_shared_chat_by_id_api_v1_chats__id__clone_shared_post | Clone Shared Chat By Id | 暂无描述 |
| /api/v1/chats/{id}/archive | POST | archive_chat_by_id_api_v1_chats__id__archive_post | Archive Chat By Id | 暂无描述 |
| /api/v1/chats/{id}/share | POST | share_chat_by_id_api_v1_chats__id__share_post | Share Chat By Id | 暂无描述 |
| /api/v1/chats/{id}/share | DELETE | delete_shared_chat_by_id_api_v1_chats__id__share_delete | Delete Shared Chat By Id | 暂无描述 |
| /api/v1/chats/{id}/folder | POST | update_chat_folder_id_by_id_api_v1_chats__id__folder_post | Update Chat Folder Id By Id | 暂无描述 |
| /api/v1/chats/{id}/tags | GET | get_chat_tags_by_id_api_v1_chats__id__tags_get | Get Chat Tags By Id | 暂无描述 |
| /api/v1/chats/{id}/tags | POST | add_tag_by_id_and_tag_name_api_v1_chats__id__tags_post | Add Tag By Id And Tag Name | 暂无描述 |
| /api/v1/chats/{id}/tags | DELETE | delete_tag_by_id_and_tag_name_api_v1_chats__id__tags_delete | Delete Tag By Id And Tag Name | 暂无描述 |
| /api/v1/chats/{id}/tags/all | DELETE | delete_all_tags_by_id_api_v1_chats__id__tags_all_delete | Delete All Tags By Id | 暂无描述 |

## notes

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/notes/ | GET | get_notes_api_v1_notes__get | Get Notes | 暂无描述 |
| /api/v1/notes/list | GET | get_note_list_api_v1_notes_list_get | Get Note List | 暂无描述 |
| /api/v1/notes/create | POST | create_new_note_api_v1_notes_create_post | Create New Note | 暂无描述 |
| /api/v1/notes/{id} | GET | get_note_by_id_api_v1_notes__id__get | Get Note By Id | 暂无描述 |
| /api/v1/notes/{id}/update | POST | update_note_by_id_api_v1_notes__id__update_post | Update Note By Id | 暂无描述 |
| /api/v1/notes/{id}/delete | DELETE | delete_note_by_id_api_v1_notes__id__delete_delete | Delete Note By Id | 暂无描述 |

## 模型管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/models/ | GET | get_models_api_v1_models__get | Get Models | 暂无描述 |
| /api/v1/models/base | GET | get_base_models_api_v1_models_base_get | Get Base Models | 暂无描述 |
| /api/v1/models/create | POST | create_new_model_api_v1_models_create_post | Create New Model | 暂无描述 |
| /api/v1/models/model | GET | get_model_by_id_api_v1_models_model_get | Get Model By Id | 暂无描述 |
| /api/v1/models/model/toggle | POST | toggle_model_by_id_api_v1_models_model_toggle_post | Toggle Model By Id | 暂无描述 |
| /api/v1/models/model/update | POST | update_model_by_id_api_v1_models_model_update_post | Update Model By Id | 暂无描述 |
| /api/v1/models/model/delete | DELETE | delete_model_by_id_api_v1_models_model_delete_delete | Delete Model By Id | 暂无描述 |
| /api/v1/models/delete/all | DELETE | delete_all_models_api_v1_models_delete_all_delete | Delete All Models | 暂无描述 |

## 知识库管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/knowledge/ | GET | get_knowledge_api_v1_knowledge__get | Get Knowledge | 暂无描述 |
| /api/v1/knowledge/list | GET | get_knowledge_list_api_v1_knowledge_list_get | Get Knowledge List | 暂无描述 |
| /api/v1/knowledge/create | POST | create_new_knowledge_api_v1_knowledge_create_post | Create New Knowledge | 暂无描述 |
| /api/v1/knowledge/reindex | POST | reindex_knowledge_files_api_v1_knowledge_reindex_post | Reindex Knowledge Files | 暂无描述 |
| /api/v1/knowledge/{id} | GET | get_knowledge_by_id_api_v1_knowledge__id__get | Get Knowledge By Id | 暂无描述 |
| /api/v1/knowledge/{id}/update | POST | update_knowledge_by_id_api_v1_knowledge__id__update_post | Update Knowledge By Id | 暂无描述 |
| /api/v1/knowledge/{id}/file/add | POST | add_file_to_knowledge_by_id_api_v1_knowledge__id__file_add_post | Add File To Knowledge By Id | 暂无描述 |
| /api/v1/knowledge/{id}/file/update | POST | update_file_from_knowledge_by_id_api_v1_knowledge__id__file_update_post | Update File From Knowledge By Id | 暂无描述 |
| /api/v1/knowledge/{id}/file/remove | POST | remove_file_from_knowledge_by_id_api_v1_knowledge__id__file_remove_post | Remove File From Knowledge By Id | 暂无描述 |
| /api/v1/knowledge/{id}/delete | DELETE | delete_knowledge_by_id_api_v1_knowledge__id__delete_delete | Delete Knowledge By Id | 暂无描述 |
| /api/v1/knowledge/{id}/reset | POST | reset_knowledge_by_id_api_v1_knowledge__id__reset_post | Reset Knowledge By Id | 暂无描述 |
| /api/v1/knowledge/{id}/files/batch/add | POST | add_files_to_knowledge_batch_api_v1_knowledge__id__files_batch_add_post | Add Files To Knowledge Batch | Add multiple files to a knowledge base |

## prompts

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/prompts/ | GET | get_prompts_api_v1_prompts__get | Get Prompts | 暂无描述 |
| /api/v1/prompts/list | GET | get_prompt_list_api_v1_prompts_list_get | Get Prompt List | 暂无描述 |
| /api/v1/prompts/create | POST | create_new_prompt_api_v1_prompts_create_post | Create New Prompt | 暂无描述 |
| /api/v1/prompts/command/{command} | GET | get_prompt_by_command_api_v1_prompts_command__command__get | Get Prompt By Command | 暂无描述 |
| /api/v1/prompts/command/{command}/update | POST | update_prompt_by_command_api_v1_prompts_command__command__update_post | Update Prompt By Command | 暂无描述 |
| /api/v1/prompts/command/{command}/delete | DELETE | delete_prompt_by_command_api_v1_prompts_command__command__delete_delete | Delete Prompt By Command | 暂无描述 |

## tools

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/tools/ | GET | get_tools_api_v1_tools__get | Get Tools | 暂无描述 |
| /api/v1/tools/list | GET | get_tool_list_api_v1_tools_list_get | Get Tool List | 暂无描述 |
| /api/v1/tools/load/url | POST | load_tool_from_url_api_v1_tools_load_url_post | Load Tool From Url | 暂无描述 |
| /api/v1/tools/export | GET | export_tools_api_v1_tools_export_get | Export Tools | 暂无描述 |
| /api/v1/tools/create | POST | create_new_tools_api_v1_tools_create_post | Create New Tools | 暂无描述 |
| /api/v1/tools/id/{id} | GET | get_tools_by_id_api_v1_tools_id__id__get | Get Tools By Id | 暂无描述 |
| /api/v1/tools/id/{id}/update | POST | update_tools_by_id_api_v1_tools_id__id__update_post | Update Tools By Id | 暂无描述 |
| /api/v1/tools/id/{id}/delete | DELETE | delete_tools_by_id_api_v1_tools_id__id__delete_delete | Delete Tools By Id | 暂无描述 |
| /api/v1/tools/id/{id}/valves | GET | get_tools_valves_by_id_api_v1_tools_id__id__valves_get | Get Tools Valves By Id | 暂无描述 |
| /api/v1/tools/id/{id}/valves/spec | GET | get_tools_valves_spec_by_id_api_v1_tools_id__id__valves_spec_get | Get Tools Valves Spec By Id | 暂无描述 |
| /api/v1/tools/id/{id}/valves/update | POST | update_tools_valves_by_id_api_v1_tools_id__id__valves_update_post | Update Tools Valves By Id | 暂无描述 |
| /api/v1/tools/id/{id}/valves/user | GET | get_tools_user_valves_by_id_api_v1_tools_id__id__valves_user_get | Get Tools User Valves By Id | 暂无描述 |
| /api/v1/tools/id/{id}/valves/user/spec | GET | get_tools_user_valves_spec_by_id_api_v1_tools_id__id__valves_user_spec_get | Get Tools User Valves Spec By Id | 暂无描述 |
| /api/v1/tools/id/{id}/valves/user/update | POST | update_tools_user_valves_by_id_api_v1_tools_id__id__valves_user_update_post | Update Tools User Valves By Id | 暂无描述 |

## memories

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/memories/ef | GET | get_embeddings_api_v1_memories_ef_get | Get Embeddings | 暂无描述 |
| /api/v1/memories/ | GET | get_memories_api_v1_memories__get | Get Memories | 暂无描述 |
| /api/v1/memories/add | POST | add_memory_api_v1_memories_add_post | Add Memory | 暂无描述 |
| /api/v1/memories/query | POST | query_memory_api_v1_memories_query_post | Query Memory | 暂无描述 |
| /api/v1/memories/reset | POST | reset_memory_from_vector_db_api_v1_memories_reset_post | Reset Memory From Vector Db | 暂无描述 |
| /api/v1/memories/delete/user | DELETE | delete_memory_by_user_id_api_v1_memories_delete_user_delete | Delete Memory By User Id | 暂无描述 |
| /api/v1/memories/{memory_id}/update | POST | update_memory_by_id_api_v1_memories__memory_id__update_post | Update Memory By Id | 暂无描述 |
| /api/v1/memories/{memory_id} | DELETE | delete_memory_by_id_api_v1_memories__memory_id__delete | Delete Memory By Id | 暂无描述 |

## folders

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/folders/ | GET | get_folders_api_v1_folders__get | Get Folders | 暂无描述 |
| /api/v1/folders/ | POST | create_folder_api_v1_folders__post | Create Folder | 暂无描述 |
| /api/v1/folders/{id} | GET | get_folder_by_id_api_v1_folders__id__get | Get Folder By Id | 暂无描述 |
| /api/v1/folders/{id} | DELETE | delete_folder_by_id_api_v1_folders__id__delete | Delete Folder By Id | 暂无描述 |
| /api/v1/folders/{id}/update | POST | update_folder_name_by_id_api_v1_folders__id__update_post | Update Folder Name By Id | 暂无描述 |
| /api/v1/folders/{id}/update/parent | POST | update_folder_parent_id_by_id_api_v1_folders__id__update_parent_post | Update Folder Parent Id By Id | 暂无描述 |
| /api/v1/folders/{id}/update/expanded | POST | update_folder_is_expanded_by_id_api_v1_folders__id__update_expanded_post | Update Folder Is Expanded By Id | 暂无描述 |

## groups

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/groups/ | GET | get_groups_api_v1_groups__get | Get Groups | 暂无描述 |
| /api/v1/groups/create | POST | create_new_group_api_v1_groups_create_post | Create New Group | 暂无描述 |
| /api/v1/groups/id/{id} | GET | get_group_by_id_api_v1_groups_id__id__get | Get Group By Id | 暂无描述 |
| /api/v1/groups/id/{id}/update | POST | update_group_by_id_api_v1_groups_id__id__update_post | Update Group By Id | 暂无描述 |
| /api/v1/groups/id/{id}/delete | DELETE | delete_group_by_id_api_v1_groups_id__id__delete_delete | Delete Group By Id | 暂无描述 |

## 文件管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/files/ | POST | upload_file_api_v1_files__post | Upload File | 暂无描述 |
| /api/v1/files/ | GET | list_files_api_v1_files__get | List Files | 暂无描述 |
| /api/v1/files/search | GET | search_files_api_v1_files_search_get | Search Files | Search for files by filename with support for wildcard patterns. |
| /api/v1/files/all | DELETE | delete_all_files_api_v1_files_all_delete | Delete All Files | 暂无描述 |
| /api/v1/files/{id} | GET | get_file_by_id_api_v1_files__id__get | Get File By Id | 暂无描述 |
| /api/v1/files/{id} | DELETE | delete_file_by_id_api_v1_files__id__delete | Delete File By Id | 暂无描述 |
| /api/v1/files/{id}/data/content | GET | get_file_data_content_by_id_api_v1_files__id__data_content_get | Get File Data Content By Id | 暂无描述 |
| /api/v1/files/{id}/data/content/update | POST | update_file_data_content_by_id_api_v1_files__id__data_content_update_post | Update File Data Content By Id | 暂无描述 |
| /api/v1/files/{id}/content | GET | get_file_content_by_id_api_v1_files__id__content_get | Get File Content By Id | 暂无描述 |
| /api/v1/files/{id}/content/html | GET | get_html_file_content_by_id_api_v1_files__id__content_html_get | Get Html File Content By Id | 暂无描述 |
| /api/v1/files/{id}/content/{file_name} | GET | get_file_content_by_id_api_v1_files__id__content__file_name__get | Get File Content By Id | 暂无描述 |

## functions

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/functions/ | GET | get_functions_api_v1_functions__get | Get Functions | 暂无描述 |
| /api/v1/functions/export | GET | get_functions_api_v1_functions_export_get | Get Functions | 暂无描述 |
| /api/v1/functions/load/url | POST | load_function_from_url_api_v1_functions_load_url_post | Load Function From Url | 暂无描述 |
| /api/v1/functions/sync | POST | sync_functions_api_v1_functions_sync_post | Sync Functions | 暂无描述 |
| /api/v1/functions/create | POST | create_new_function_api_v1_functions_create_post | Create New Function | 暂无描述 |
| /api/v1/functions/id/{id} | GET | get_function_by_id_api_v1_functions_id__id__get | Get Function By Id | 暂无描述 |
| /api/v1/functions/id/{id}/toggle | POST | toggle_function_by_id_api_v1_functions_id__id__toggle_post | Toggle Function By Id | 暂无描述 |
| /api/v1/functions/id/{id}/toggle/global | POST | toggle_global_by_id_api_v1_functions_id__id__toggle_global_post | Toggle Global By Id | 暂无描述 |
| /api/v1/functions/id/{id}/update | POST | update_function_by_id_api_v1_functions_id__id__update_post | Update Function By Id | 暂无描述 |
| /api/v1/functions/id/{id}/delete | DELETE | delete_function_by_id_api_v1_functions_id__id__delete_delete | Delete Function By Id | 暂无描述 |
| /api/v1/functions/id/{id}/valves | GET | get_function_valves_by_id_api_v1_functions_id__id__valves_get | Get Function Valves By Id | 暂无描述 |
| /api/v1/functions/id/{id}/valves/spec | GET | get_function_valves_spec_by_id_api_v1_functions_id__id__valves_spec_get | Get Function Valves Spec By Id | 暂无描述 |
| /api/v1/functions/id/{id}/valves/update | POST | update_function_valves_by_id_api_v1_functions_id__id__valves_update_post | Update Function Valves By Id | 暂无描述 |
| /api/v1/functions/id/{id}/valves/user | GET | get_function_user_valves_by_id_api_v1_functions_id__id__valves_user_get | Get Function User Valves By Id | 暂无描述 |
| /api/v1/functions/id/{id}/valves/user/spec | GET | get_function_user_valves_spec_by_id_api_v1_functions_id__id__valves_user_spec_get | Get Function User Valves Spec By Id | 暂无描述 |
| /api/v1/functions/id/{id}/valves/user/update | POST | update_function_user_valves_by_id_api_v1_functions_id__id__valves_user_update_post | Update Function User Valves By Id | 暂无描述 |

## evaluations

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/evaluations/config | GET | get_config_api_v1_evaluations_config_get | Get Config | 暂无描述 |
| /api/v1/evaluations/config | POST | update_config_api_v1_evaluations_config_post | Update Config | 暂无描述 |
| /api/v1/evaluations/feedbacks/all | GET | get_all_feedbacks_api_v1_evaluations_feedbacks_all_get | Get All Feedbacks | 暂无描述 |
| /api/v1/evaluations/feedbacks/all | DELETE | delete_all_feedbacks_api_v1_evaluations_feedbacks_all_delete | Delete All Feedbacks | 暂无描述 |
| /api/v1/evaluations/feedbacks/all/export | GET | get_all_feedbacks_api_v1_evaluations_feedbacks_all_export_get | Get All Feedbacks | 暂无描述 |
| /api/v1/evaluations/feedbacks/user | GET | get_feedbacks_api_v1_evaluations_feedbacks_user_get | Get Feedbacks | 暂无描述 |
| /api/v1/evaluations/feedbacks | DELETE | delete_feedbacks_api_v1_evaluations_feedbacks_delete | Delete Feedbacks | 暂无描述 |
| /api/v1/evaluations/feedback | POST | create_feedback_api_v1_evaluations_feedback_post | Create Feedback | 暂无描述 |
| /api/v1/evaluations/feedback/{id} | GET | get_feedback_by_id_api_v1_evaluations_feedback__id__get | Get Feedback By Id | 暂无描述 |
| /api/v1/evaluations/feedback/{id} | POST | update_feedback_by_id_api_v1_evaluations_feedback__id__post | Update Feedback By Id | 暂无描述 |
| /api/v1/evaluations/feedback/{id} | DELETE | delete_feedback_by_id_api_v1_evaluations_feedback__id__delete | Delete Feedback By Id | 暂无描述 |

## utils

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/utils/gravatar | GET | get_gravatar_api_v1_utils_gravatar_get | Get Gravatar | 暂无描述 |
| /api/v1/utils/code/format | POST | format_code_api_v1_utils_code_format_post | Format Code | 暂无描述 |
| /api/v1/utils/code/execute | POST | execute_code_api_v1_utils_code_execute_post | Execute Code | 暂无描述 |
| /api/v1/utils/markdown | POST | get_html_from_markdown_api_v1_utils_markdown_post | Get Html From Markdown | 暂无描述 |
| /api/v1/utils/pdf | POST | download_chat_as_pdf_api_v1_utils_pdf_post | Download Chat As Pdf | 暂无描述 |
| /api/v1/utils/db/download | GET | download_db_api_v1_utils_db_download_get | Download Db | 暂无描述 |
| /api/v1/utils/litellm/config | GET | download_litellm_config_yaml_api_v1_utils_litellm_config_get | Download Litellm Config Yaml | 暂无描述 |

## HSAI 素材管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/materials/folders | GET | get_material_folders_api_v1_hsai_materials_folders_get | 获取素材文件夹 | 获取用户的素材文件夹树形结构，包含子文件夹和素材数量统计。

Args:
    query (str, optional): 搜索关键词，用于按文件夹名称进行模糊搜索
    user: 已认证的用户对象
    
Returns:
    List[HSAIMaterialFolderResponse]: 文件夹树形结构列表 |
| /api/v1/hsai/materials/folders | POST | create_material_folder_api_v1_hsai_materials_folders_post | 创建素材文件夹 | 创建新的素材文件夹。 |
| /api/v1/hsai/materials/folders/{folder_id}/rename | POST | rename_material_folder_api_v1_hsai_materials_folders__folder_id__rename_post | 重命名素材文件夹 | 重命名素材文件夹。

Args:
    folder_id (str): 文件夹唯一标识符
    form_data (HSAIMaterialFolderForm): 包含新文件夹名称的表单数据
    user: 已认证的用户对象
    
Returns:
    HSAIMaterialFolderResponse: 更新后的文件夹信息
    
Raises:
    HTTPException: 404 - 文件夹不存在或无权限访问
    HTTPException: 400 - 文件夹名称已存在
    HTTPException: 500 - 更新失败 |
| /api/v1/hsai/materials/folders/{folder_id} | DELETE | delete_material_folder_api_v1_hsai_materials_folders__folder_id__delete | 删除素材文件夹 | 删除指定的素材文件夹。

Args:
    folder_id (str): 文件夹唯一标识符
    user: 已认证的用户对象
    
Returns:
    bool: 删除成功返回true
    
Raises:
    HTTPException: 404 - 文件夹不存在或无权限访问
    HTTPException: 400 - 文件夹不为空，无法删除
    HTTPException: 500 - 删除失败 |
| /api/v1/hsai/materials/upload | POST | upload_material_api_v1_hsai_materials_upload_post | 上传素材 | 上传素材文件，支持本地存储和OSS存储。

支持多种文件格式的上传，包括图片、视频、音频、文档等。
支持压缩包上传，系统会自动解析压缩包内的文件并按规则重命名。
文件将存储在本地或上传到阿里云OSS存储，上传后可选择进行AI自动分析。

Args:
    file (UploadFile): 要上传的文件（支持单个文件或压缩包）
    name (str, optional): 素材名称，默认使用文件名
    description (str, optional): 素材描述
    folder_id (str, optional): 目标文件夹ID
    tags (str, optional): 标签列表，JSON格式字符串
    auto_analyze (bool): 是否自动进行AI分析，默认True
    scene_code (str, optional): 场景代码
    technique_code (str, optional): 手法代码
    properties_code (str, optional): 属性代码，JSON格式字符串
    user: 已认证的用户对象
    
Returns:
    List[HSAIMaterialResponse]: 上传成功的素材信息列表
    - id: 素材ID
    - name: 素材名称
    - file_path: 存储路径
    - file_size: 文件大小
    - mime_type: 文件MIME类型
    - material_type: 素材类型
    - upload_url: 文件访问URL
    
Raises:
    HTTPException: 400 - 文件格式不支持或文件过大
    HTTPException: 500 - 上传失败或服务器错误 |
| /api/v1/hsai/materials/{material_id}/download | GET | get_material_download_url_api_v1_hsai_materials__material_id__download_get | 获取素材下载链接 | 获取素材的OSS下载链接。

返回可直接访问的OSS URL，支持CDN加速。

Args:
    material_id (str): 素材ID
    user: 已认证的用户对象
    
Returns:
    dict: 包含下载URL和文件信息
    - download_url: OSS访问URL
    - filename: 文件名
    - file_size: 文件大小
    - mime_type: 文件MIME类型
    
Raises:
    HTTPException: 404 - 素材不存在或无权限访问
    HTTPException: 500 - 服务器内部错误
    
Note:
    - 每次访问会增加素材的使用次数统计
    - 只能访问属于当前用户的素材
    - 返回的是OSS直链，支持CDN加速 |
| /api/v1/hsai/materials/ | GET | get_materials_api_v1_hsai_materials__get | 获取素材列表 | 获取用户的素材列表（分页）。

支持按文件夹、类型过滤和关键词搜索，支持分页查询。

Args:
    folder_id (str, optional): 文件夹ID，为空则获取根目录素材
    material_type (str, optional): 素材类型过滤：image(图片)、video(视频)、audio(音频)、text(文本)、document(文档)
    query (str, optional): 搜索关键词，用于按名称、描述、标签进行模糊搜索
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    user: 已认证的用户对象
    
Returns:
    PaginatedHSAIMaterialResponse: 分页的素材列表
    - data: 素材列表
    - pagination: 分页信息 |
| /api/v1/hsai/materials/{material_id} | GET | get_material_api_v1_hsai_materials__material_id__get | 获取素材详情 | 获取指定素材的详细信息。 |
| /api/v1/hsai/materials/{material_id}/properties | GET | get_material_properties_api_v1_hsai_materials__material_id__properties_get | 获取素材属性 | 获取指定素材的详细属性信息。

Args:
    material_id (str): 素材ID
    user: 已认证的用户对象
    
Returns:
    MaterialPropertiesResponse: 素材属性信息 |
| /api/v1/hsai/materials/statistics | GET | get_material_stats_api_v1_hsai_materials_statistics_get | 获取素材统计 | 获取用户的素材统计信息。

包括总数量、各类型数量、存储使用量等。 |

## HSAI 素材管理 - 回收站

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/materials/{material_id}/move-to-recovery | POST | move_material_to_recovery_api_v1_hsai_materials__material_id__move_to_recovery_post | 移入回收站（软删除） | 将指定素材从原目录移动到回收站目录，在数据库中更新删除标志位和原目录信息，记录操作日志

Args:
    material_id (str): 素材唯一标识符
    request (MoveToRecoveryRequest): 请求参数
    user: 已认证的用户对象
    
Returns:
    HSAIMaterialResponse: 更新后的素材信息 |
| /api/v1/hsai/materials/recovery/{material_id}/restore | POST | restore_material_api_v1_hsai_materials_recovery__material_id__restore_post | 还原文件 | 将回收站中的文件还原到原始目录，更新数据库记录，记录操作日志

Args:
    material_id (str): 素材唯一标识符
    user: 已认证的用户对象
    
Returns:
    HSAIMaterialResponse: 更新后的素材信息

Note:
    还原操作将自动将素材还原到其原始目录（original_directory字段记录的位置） |
| /api/v1/hsai/materials/{material_id}/permanent-delete | DELETE | permanent_delete_material_api_v1_hsai_materials__material_id__permanent_delete_delete | 永久删除文件 | 根据素材ID在素材表中找到对应的记录，通过素材文件的位置信息确定需要删除的OSS文件
（企业目录或回收站目录中的文件），彻底删除OSS文件和数据库记录，记录操作日志。
此接口统一处理所有永久删除操作，客户端无需关心文件具体位置。

Args:
    material_id (str): 素材唯一标识符
    request (PermanentDeleteRequest): 请求参数
    user: 已认证的用户对象
    
Returns:
    bool: 删除成功返回True |
| /api/v1/hsai/materials/recovery/list | GET | get_recovery_materials_api_v1_hsai_materials_recovery_list_get | 获取回收站文件列表 | 获取当前用户回收站中的文件列表

Args:
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    sort_by (str): 排序字段（delete_time/name/size），默认delete_time
    order (str): 排序方式（asc/desc），默认desc
    user: 已认证的用户对象
    
Returns:
    PaginatedHSAIMaterialResponse: 分页的回收站文件列表
    - data: 回收站文件列表
    - pagination: 分页信息
      - total: 总记录数
      - page: 当前页码
      - size: 每页大小
      - total_pages: 总页数 |
| /api/v1/hsai/materials/recovery/batch-operation | POST | batch_operation_recovery_materials_api_v1_hsai_materials_recovery_batch_operation_post | 批量操作回收站文件 | 对回收站中的多个文件进行批量还原或删除操作

Args:
    request (BatchOperationRequest): 请求参数
    user: 已认证的用户对象
    
Returns:
    bool: 操作成功返回True |

## HSAI 素材管理 - 分类

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/materials/categories | GET | get_material_categories_api_v1_hsai_materials_categories_get | 获取素材分类列表 | 获取素材分类列表（分页），可按分类类型过滤。

Args:
    category_type (str, optional): 分类类型过滤
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    
Returns:
    PaginatedHSAIMaterialCategoryResponse: 分页的分类列表
    - data: 分类列表
    - pagination: 分页信息
      - total: 总记录数
      - page: 当前页码
      - size: 每页大小
      - total_pages: 总页数 |
| /api/v1/hsai/materials/categories | POST | create_material_category_api_v1_hsai_materials_categories_post | 创建素材分类 | 创建新的素材分类。

Args:
    form_data (HSAIMaterialCategoryForm): 分类表单数据
    
Returns:
    HSAIMaterialCategoryResponse: 创建的分类信息 |
| /api/v1/hsai/materials/categories/{category_id} | PUT | update_material_category_api_v1_hsai_materials_categories__category_id__put | 更新素材分类 | 更新指定的素材分类。

Args:
    category_id (str): 分类ID
    form_data (HSAIMaterialCategoryForm): 分类表单数据
    
Returns:
    HSAIMaterialCategoryResponse: 更新的分类信息 |
| /api/v1/hsai/materials/categories/{category_id} | DELETE | delete_material_category_api_v1_hsai_materials_categories__category_id__delete | 删除素材分类 | 删除指定的素材分类（软删除）。

Args:
    category_id (str): 分类ID
    
Returns:
    bool: 删除成功返回True |

## HSAI 素材管理 - 日志

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/materials/logs | POST | log_file_operation_api_v1_hsai_materials_logs_post | 记录文件操作日志 | 记录文件操作日志

Args:
    form_data (FileOperationLogForm): 日志表单数据
    user: 已认证的用户对象
    
Returns:
    HSAIFileOperationLogResponse: 创建的日志信息 |
| /api/v1/hsai/materials/logs | GET | get_file_operation_logs_api_v1_hsai_materials_logs_get | 查询文件操作日志 | 查询文件操作日志（分页）

Args:
    material_id (str, optional): 素材唯一标识符
    enterprise_id (str, optional): 企业ID
    operation_type (str, optional): 操作类型
    operator_id (str, optional): 操作人ID
    start_time (int, optional): 查询起始时间
    end_time (int, optional): 查询结束时间
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    user: 已认证的用户对象
    
Returns:
    PaginatedHSAIFileOperationLogResponse: 分页的文件操作日志列表
    - data: 日志列表
    - pagination: 分页信息
      - total: 总记录数
      - page: 当前页码
      - size: 每页大小
      - total_pages: 总页数 |
| /api/v1/hsai/materials/{material_id}/history | GET | get_material_history_api_v1_hsai_materials__material_id__history_get | 获取文件操作历史 | 获取指定文件的所有操作历史记录（分页）

Args:
    material_id (str): 素材唯一标识符
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    user: 已认证的用户对象
    
Returns:
    PaginatedHSAIFileOperationLogResponse: 分页的文件操作历史记录列表
    - data: 历史记录列表
    - pagination: 分页信息
      - total: 总记录数
      - page: 当前页码
      - size: 每页大小
      - total_pages: 总页数 |

## HSAI 任务管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/tasks/statistics | GET | get_task_stats_api_v1_hsai_tasks_statistics_get | 获取任务统计 | 获取任务统计信息。

提供用户任务的详细统计数据，用于仪表板展示和性能分析。

Args:
    user: 已认证的用户对象
    
Returns:
    TaskStatsResponse: 统计信息
    - total_tasks: 任务总数量
    - pending_tasks: 待执行任务数量
    - in_progress_tasks: 执行中任务数量
    - completed_tasks: 已完成任务数量
    - failed_tasks: 失败任务数量
    - tasks_by_type: 按类型分组的任务数量
      - video_creation: 视频创作任务数量
      - content_analysis: 内容分析任务数量
      - image_generation: 图像生成任务数量
      - text_processing: 文本处理任务数量
    - avg_completion_time: 平均完成时间（秒）
    
Raises:
    HTTPException: 500 - 服务器内部错误
    
Note:
    - 统计数据仅包含当前用户的任务
    - 平均完成时间基于已完成任务计算
    - 用于性能监控和用户行为分析 |
| /api/v1/hsai/tasks/ | GET | get_tasks_api_v1_hsai_tasks__get | 获取任务列表 | 获取用户的任务列表（分页）。

支持按状态、类型、指派人和聊天会话进行过滤，返回任务的详细信息和预估执行时间。

Args:
    status (Optional[str]): 任务状态过滤
    - "pending": 待执行
    - "in_progress": 执行中
    - "completed": 已完成
    - "failed": 执行失败
    - "cancelled": 已取消
    task_type (Optional[str]): 任务类型过滤
    - "video_creation": 视频创作
    - "content_analysis": 内容分析
    - "image_generation": 图像生成
    - "text_processing": 文本处理
    assignee_id (Optional[str]): 指派人ID过滤
    chat_id (Optional[str]): 聊天会话ID过滤
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    user: 已认证的用户对象
    
Returns:
    PaginatedHSAITaskResponse: 分页的任务列表
    - data: 任务列表
    - pagination: 分页信息
      - total: 总记录数
      - page: 当前页码
      - size: 每页大小
      - total_pages: 总页数
    
Raises:
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/tasks/ | POST | create_task_api_v1_hsai_tasks__post | 创建任务 | 创建新的AI任务。

创建任务后会自动生成对应的聊天卡片，并通过WebSocket通知前端。

Args:
    form_data (HSAITaskForm): 任务创建表单
    - title: 任务标题（必填）
    - description: 任务描述（可选）
    - task_type: 任务类型（必填）
    - chat_id: 关联的聊天会话ID（可选）
    - parameters: 任务参数（JSON格式）
    - priority: 任务优先级（1-10，默认5）
    user: 已认证的用户对象
    
Returns:
    HSAITaskResponse: 创建的任务信息
    
Raises:
    HTTPException: 400 - 创建失败
    HTTPException: 500 - 服务器内部错误
    
Note:
    - 如果指定了chat_id，会自动创建任务卡片
    - 创建成功后会通过WebSocket发送通知
    - 任务初始状态为"pending" |
| /api/v1/hsai/tasks/{task_id} | GET | get_task_api_v1_hsai_tasks__task_id__get | 获取任务详情 | 获取单个任务详情 |
| /api/v1/hsai/tasks/{task_id} | PUT | update_task_api_v1_hsai_tasks__task_id__put | 更新任务 | 更新任务 |
| /api/v1/hsai/tasks/{task_id}/recurring/activate | POST | activate_recurring_task_api_v1_hsai_tasks__task_id__recurring_activate_post | 启动循环任务 | 暂无描述 |
| /api/v1/hsai/tasks/{task_id}/recurring/pause | POST | pause_recurring_task_api_v1_hsai_tasks__task_id__recurring_pause_post | 暂停循环任务 | 暂无描述 |
| /api/v1/hsai/tasks/{task_id}/recurring/resume | POST | resume_recurring_task_api_v1_hsai_tasks__task_id__recurring_resume_post | 恢复循环任务 | 暂无描述 |
| /api/v1/hsai/tasks/{task_id}/recurring/handover | POST | handover_recurring_task_api_v1_hsai_tasks__task_id__recurring_handover_post | 循环任务交接外部控制 | 暂无描述 |
| /api/v1/hsai/tasks/{task_id}/recurring/sync | POST | sync_recurring_task_api_v1_hsai_tasks__task_id__recurring_sync_post | 同步循环任务状态 | 暂无描述 |
| /api/v1/hsai/tasks/{task_id}/recurring/logs | GET | get_recurring_logs_api_v1_hsai_tasks__task_id__recurring_logs_get | 循环任务状态日志 | 暂无描述 |
| /api/v1/hsai/tasks/{task_id}/start | POST | start_task_api_v1_hsai_tasks__task_id__start_post | 启动任务 | 启动任务执行。

将待执行状态的任务启动，开始实际的AI处理流程。

Args:
    task_id (str): 要启动的任务ID
    user: 已认证的用户对象
    
Returns:
    HSAITaskResponse: 更新后的任务信息
    
Raises:
    HTTPException: 404 - 任务不存在或无权限访问
    HTTPException: 400 - 任务状态不允许启动
    HTTPException: 500 - 启动失败
    
Note:
    - 只有"pending"状态的任务可以启动
    - 启动后任务状态变为"in_progress"
    - 客户端需要主动轮询获取任务状态 |
| /api/v1/hsai/tasks/{task_id}/simulate | POST | simulate_recurring_schedule_api_v1_hsai_tasks__task_id__simulate_post | 模拟循环任务调度 | 暂无描述 |
| /api/v1/hsai/tasks/{task_id}/cancel | POST | cancel_task_api_v1_hsai_tasks__task_id__cancel_post | 取消任务 | 取消任务执行。

停止正在执行或待执行的任务，释放相关资源。

Args:
    task_id (str): 要取消的任务ID
    user: 已认证的用户对象
    
Returns:
    HSAITaskResponse: 更新后的任务信息
    
Raises:
    HTTPException: 404 - 任务不存在或无权限访问
    HTTPException: 400 - 任务已完成或已取消，无法取消
    HTTPException: 500 - 取消失败
    
Note:
    - 已完成或已取消的任务无法再次取消
    - 取消后任务状态变为"cancelled"
    - 客户端需要主动轮询获取任务状态 |
| /api/v1/hsai/tasks/{task_id}/progress | PUT | update_task_progress_api_v1_hsai_tasks__task_id__progress_put | 更新任务进度 | 更新任务执行进度。

通常由后台任务处理进程调用，实时更新任务的执行进度。

Args:
    task_id (str): 任务ID
    progress (int): 进度百分比（0-100）
    user: 已认证的用户对象
    
Returns:
    bool: 更新是否成功
    
Raises:
    HTTPException: 404 - 任务不存在或无权限访问
    HTTPException: 500 - 更新失败
    
Note:
    - 进度值应在0-100之间
    - 客户端需要主动轮询获取任务进度
    - 通常由异步任务处理器调用 |
| /api/v1/hsai/tasks/{task_id}/assign | POST | assign_task_api_v1_hsai_tasks__task_id__assign_post | 指派任务 | 指派任务给指定用户。

Args:
    task_id (str): 要指派的任务ID
    assignee_id (str): 指派给的用户ID
    user: 已认证的用户对象
    
Returns:
    HSAITaskResponse: 更新后的任务信息
    
Raises:
    HTTPException: 404 - 任务不存在或无权限访问
    HTTPException: 500 - 指派失败
    
Note:
    - 任务创建者或管理员可以指派任务
    - 指派后会更新任务的assignee_id字段 |
| /api/v1/hsai/tasks/cards/chat/{chat_id} | GET | get_chat_cards_api_v1_hsai_tasks_cards_chat__chat_id__get | 获取聊天卡片 | 获取聊天会话中的卡片列表（分页）。

返回指定聊天会话中的所有卡片，支持分页查询。

Args:
    chat_id (str): 聊天会话ID
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    user: 已认证的用户对象
    
Returns:
    PaginatedHSAICardResponse: 分页的卡片列表
    - data: 卡片列表
    - pagination: 分页信息
      - total: 总记录数
      - page: 当前页码
      - size: 每页大小
      - total_pages: 总页数
    
Raises:
    HTTPException: 500 - 服务器内部错误
    
Note:
    - 卡片按创建时间排序
    - 如果卡片关联了任务，会同时返回任务状态
    - 用于在聊天界面中显示交互式内容 |
| /api/v1/hsai/tasks/cards | POST | create_card_api_v1_hsai_tasks_cards_post | 创建卡片 | 创建新卡片 |
| /api/v1/hsai/tasks/cards/{card_id} | PUT | update_card_api_v1_hsai_tasks_cards__card_id__put | 更新卡片 | 更新卡片 |

## HSAI AI服务

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/ai/generate-video-script | POST | generate_video_script_task_api_v1_hsai_ai_generate_video_script_post | 生成视频脚本（任务集成） | 生成视频脚本（集成任务系统）

根据产品信息和目标受众生成营销视频脚本。
自动创建任务并跟踪执行状态。 |
| /api/v1/hsai/ai/analyze-product | POST | analyze_product_task_api_v1_hsai_ai_analyze_product_post | 产品市场分析（任务集成） | 产品市场分析（集成任务系统）

分析产品定位、竞争优势与营销策略建议。
自动创建任务并跟踪执行状态。 |
| /api/v1/hsai/ai/generate-content-ideas | POST | generate_content_ideas_task_api_v1_hsai_ai_generate_content_ideas_post | 生成内容创意（任务集成） | 生成内容创意（集成任务系统）

基于行业和目标受众生成内容创意。
自动创建任务并跟踪执行状态。 |
| /api/v1/hsai/ai/optimize-material | POST | optimize_material_task_api_v1_hsai_ai_optimize_material_post | 优化素材内容（任务集成） | 优化素材内容（集成任务系统）

基于使用场景优化素材描述和标签。
自动创建任务并跟踪执行状态。 |
| /api/v1/hsai/ai/chat | POST | ai_chat_task_api_v1_hsai_ai_chat_post | HSAI智能对话（任务集成） | HSAI智能对话（集成任务系统）

基于用户输入提供智能响应和建议。
自动创建任务并跟踪执行状态。 |
| /api/v1/hsai/ai/task-templates | GET | get_ai_task_templates_api_v1_hsai_ai_task_templates_get | 获取AI任务模板 | 获取AI任务模板列表。

返回所有可用的AI任务类型和对应的参数模板。 |

## HSAI 仪表板

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/dashboard/overview | GET | get_dashboard_overview_api_v1_hsai_dashboard_overview_get | 获取工作台概览 | 获取用户工作台概览数据。

提供用户的核心数据统计，包括任务、素材、对话等关键指标。

Args:
    user: 已认证的用户对象
    
Returns:
    DashboardOverviewResponse: 工作台概览数据
    - total_tasks: 总任务数
    - active_tasks: 活跃任务数
    - completed_tasks: 已完成任务数
    - failed_tasks: 失败任务数
    - total_materials: 总素材数
    - total_chats: 总对话数
    - storage_used: 已使用存储空间(MB)
    - storage_limit: 存储空间限制(MB)
    
Raises:
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/dashboard/kpi | GET | get_kpi_metrics_api_v1_hsai_dashboard_kpi_get | 获取KPI指标 | 获取用户KPI指标数据。

计算用户在指定时间范围内的关键绩效指标。

Args:
    days (int): 统计天数，默认30天
    user: 已认证的用户对象
    
Returns:
    KPIMetrics: KPI指标数据
    - task_completion_rate: 任务完成率(%)
    - avg_task_duration: 平均任务时长(小时)
    - daily_active_rate: 日活跃率(%)
    - material_usage_rate: 素材使用率(%)
    - ai_interaction_count: AI交互次数
    - productivity_score: 生产力评分(0-100)
    
Raises:
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/dashboard/recent-activities | GET | get_recent_activities_api_v1_hsai_dashboard_recent_activities_get | 获取最近活动 | 获取用户最近活动记录。

返回用户最近的操作活动，包括任务、素材、对话等各类活动。

Args:
    limit (int): 返回数量限制，默认20条
    activity_type (Optional[str]): 活动类型过滤
    user: 已认证的用户对象
    
Returns:
    List[RecentActivity]: 最近活动列表
    - id: 活动唯一标识
    - type: 活动类型
    - title: 活动标题
    - description: 活动描述
    - timestamp: 活动时间戳
    - status: 活动状态
    - metadata: 额外元数据
    
Raises:
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/dashboard/stats | GET | get_dashboard_stats_api_v1_hsai_dashboard_stats_get | 获取工作台统计数据 | 获取工作台完整统计数据。

包含概览、KPI指标、最近活动和趋势数据的综合统计信息。

Args:
    days (int): 趋势统计天数，默认7天
    user: 已认证的用户对象
    
Returns:
    DashboardStatsResponse: 完整统计数据
    
Raises:
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/dashboard/quick-actions/create-task | POST | quick_create_task_api_v1_hsai_dashboard_quick_actions_create_task_post | 快速创建任务 | 快速创建任务。

从工作台快速创建新任务的便捷接口。

Args:
    title (str): 任务标题
    task_type (str): 任务类型，默认为general
    user: 已认证的用户对象
    
Returns:
    dict: 创建结果
    - success: 是否成功
    - task_id: 创建的任务ID
    - message: 结果消息
    
Raises:
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/dashboard/system-status | GET | get_system_status_api_v1_hsai_dashboard_system_status_get | 获取系统状态 | 获取系统状态信息。

返回系统运行状态和健康检查信息。

Returns:
    dict: 系统状态信息
    - status: 系统状态
    - uptime: 运行时间
    - version: 系统版本
    - features: 可用功能列表 |

## HSAI 对话管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/chat/statistics | GET | get_chat_stats_api_v1_hsai_chat_statistics_get | 获取对话统计 | 获取用户对话统计信息。

Args:
    days (int): 统计天数，默认30天
    user: 已认证的用户对象
    
Returns:
    ChatStatsResponse: 对话统计数据 |
| /api/v1/hsai/chat/sessions | GET | get_chat_sessions_api_v1_hsai_chat_sessions_get | 获取对话会话列表 | 获取用户的对话会话列表。

返回用户的所有对话会话，支持分页和过滤。

Args:
    limit (int): 返回数量限制，默认50
    offset (int): 偏移量，默认0
    tag (Optional[str]): 标签过滤
    task_id (Optional[str]): 任务ID过滤
    user: 已认证的用户对象
    
Returns:
    List[ChatSessionResponse]: 对话会话列表
    
Raises:
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/chat/sessions | POST | create_chat_session_api_v1_hsai_chat_sessions_post | 创建对话会话 | 创建新的对话会话。

创建一个新的AI对话会话，可以关联到特定任务。

Args:
    form_data (ChatSessionForm): 会话创建表单
    user: 已认证的用户对象
    
Returns:
    ChatSessionResponse: 创建的会话信息
    
Raises:
    HTTPException: 400 - 创建失败
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/chat/sessions/{session_id} | GET | get_chat_session_api_v1_hsai_chat_sessions__session_id__get | 获取会话详情 | 获取指定对话会话的详细信息。

Args:
    session_id (str): 会话ID
    user: 已认证的用户对象
    
Returns:
    ChatSessionResponse: 会话详细信息
    
Raises:
    HTTPException: 404 - 会话不存在或无权限访问
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/chat/sessions/{session_id} | PUT | update_chat_session_api_v1_hsai_chat_sessions__session_id__put | 更新会话信息 | 更新对话会话信息。

Args:
    session_id (str): 会话ID
    title (Optional[str]): 新标题
    tags (Optional[List[str]]): 新标签列表
    is_pinned (Optional[bool]): 是否置顶
    user: 已认证的用户对象
    
Returns:
    dict: 更新结果
    
Raises:
    HTTPException: 404 - 会话不存在或无权限访问
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/chat/sessions/{session_id} | DELETE | delete_chat_session_api_v1_hsai_chat_sessions__session_id__delete | 删除会话 | 删除对话会话。

Args:
    session_id (str): 会话ID
    user: 已认证的用户对象
    
Returns:
    dict: 删除结果
    
Raises:
    HTTPException: 404 - 会话不存在或无权限访问
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/chat/sessions/{session_id}/messages | GET | get_chat_messages_api_v1_hsai_chat_sessions__session_id__messages_get | 获取会话消息 | 获取对话会话的消息列表。

Args:
    session_id (str): 会话ID
    limit (int): 返回数量限制
    offset (int): 偏移量
    user: 已认证的用户对象
    
Returns:
    List[ChatMessageResponse]: 消息列表
    
Raises:
    HTTPException: 404 - 会话不存在或无权限访问
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/chat/sessions/{session_id}/messages | POST | send_chat_message_api_v1_hsai_chat_sessions__session_id__messages_post | 发送消息 | 向对话会话发送消息。

Args:
    session_id (str): 会话ID
    message_data (ChatMessageForm): 消息数据
    user: 已认证的用户对象
    
Returns:
    ChatMessageResponse: 发送的消息信息
    
Raises:
    HTTPException: 404 - 会话不存在或无权限访问
    HTTPException: 500 - 服务器内部错误 |
| /api/v1/hsai/chat/search | GET | search_chat_content_api_v1_hsai_chat_search_get | 搜索对话内容 | 搜索用户的对话内容。

Args:
    query (str): 搜索关键词
    limit (int): 返回数量限制
    user: 已认证的用户对象
    
Returns:
    dict: 搜索结果
    
Raises:
    HTTPException: 500 - 服务器内部错误 |

## 工作流管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/api/v1/workflows/trigger | POST | trigger_workflow_api_v1_api_v1_workflows_trigger_post | 触发工作流 | 触发指定的工作流执行 |

## HSAI Video Learning

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/video-learning/videos | GET | get_pending_videos_api_v1_hsai_video_learning_videos_get | List videos with learning status | List videos and merge learning status under the current business tenant. |
| /api/v1/hsai/video-learning/start-learning | POST | start_video_learning_api_v1_hsai_video_learning_start_learning_post | Start learning a video | Trigger the learning workflow for a given video. |
| /api/v1/hsai/video-learning/test | GET | test_endpoint_api_v1_hsai_video_learning_test_get | Health check for video learning router | Simple test endpoint. |

## HSAI 项目管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/hsai/projects/ | GET | get_projects_api_v1_hsai_projects__get | 鑾峰彇椤圭洰鍒楄〃 | 鑾峰彇鐢ㄦ埛鐨勯」鐩垪琛紙鍒嗛〉锛夈€?

Args:
    status (Optional[str]): 椤圭洰鐘舵€佽繃婊?
    ps (int): 鍒嗛〉澶у皬锛岃寖鍥?-100
    pi (int): 鍒嗛〉绱㈠紩锛屼粠1寮€濮?
    user: 宸茶璇佺殑鐢ㄦ埛瀵硅薄
    
Returns:
    PaginatedHSAIProjectResponse: 鍒嗛〉鐨勯」鐩垪琛? |
| /api/v1/hsai/projects/ | POST | create_project_api_v1_hsai_projects__post | 鍒涘缓椤圭洰 | 鍒涘缓鏂扮殑椤圭洰銆?

鍒涘缓椤圭洰鍚庝細鑷姩鍒涘缓涓荤嚎浠诲姟銆?

Args:
    form_data (HSAIProjectForm): 椤圭洰鍒涘缓琛ㄥ崟
    user: 宸茶璇佺殑鐢ㄦ埛瀵硅薄
    
Returns:
    HSAIProjectResponse: 鍒涘缓鐨勯」鐩俊鎭? |
| /api/v1/hsai/projects/{project_id} | GET | get_project_api_v1_hsai_projects__project_id__get | 鑾峰彇椤圭洰璇︽儏 | 鑾峰彇鍗曚釜椤圭洰璇︽儏 |
| /api/v1/hsai/projects/{project_id} | PUT | update_project_api_v1_hsai_projects__project_id__put | 鏇存柊椤圭洰 | 鏇存柊椤圭洰 |
| /api/v1/hsai/projects/{project_id} | DELETE | delete_project_api_v1_hsai_projects__project_id__delete | 鍒犻櫎椤圭洰 | 鍒犻櫎椤圭洰 |
| /api/v1/hsai/projects/{project_id}/tasks | GET | get_project_tasks_api_v1_hsai_projects__project_id__tasks_get | 获取项目任务列表 | 获取指定项目下的所有任务（含主要任务与循环任务）。需要项目所属用户访问权限。 |
| /api/v1/hsai/projects/{project_id}/summary | GET | get_project_summary_api_v1_hsai_projects__project_id__summary_get | 项目任务摘要 | 返回项目概要（蓝图版本/同步状态/计划统计）、主要任务完成度、循环任务条目与近期状态日志等。 |

## 组织管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/organizations/ | GET | get_organizations_api_v1_organizations__get | 获取组织列表 | 分页获取组织列表，仅系统管理员可访问。参数：page（页码，>=1），size（页大小，1-100）。返回包含分页信息的组织列表。 |
| /api/v1/organizations/ | POST | create_organization_api_v1_organizations__post | 创建组织 | 创建新的组织，仅系统管理员可访问。 |
| /api/v1/organizations/{organization_id} | GET | get_organization_by_id_api_v1_organizations__organization_id__get | 获取组织详情 | 按 ID 获取组织详情，需具备该组织的访问权限。未找到返回 404。 |
| /api/v1/organizations/{organization_id} | POST | update_organization_api_v1_organizations__organization_id__post | 更新组织信息 | 更新指定组织的基础信息，需组织管理员或系统管理员权限。 |
| /api/v1/organizations/{organization_id} | DELETE | delete_organization_api_v1_organizations__organization_id__delete | 删除组织 | 删除指定组织，仅系统管理员可访问。若组织下仍有关联用户或项目，将返回 400。 |
| /api/v1/organizations/{organization_id}/users | GET | get_organization_users_api_v1_organizations__organization_id__users_get | 获取组织用户列表 | 分页获取指定组织的用户列表，需组织访问权限。参数：page，size。 |
| /api/v1/organizations/{organization_id}/users/{user_id} | POST | add_user_to_organization_api_v1_organizations__organization_id__users__user_id__post | 将用户加入组织 | 将指定用户加入组织并可设置其为组织管理员。 |
| /api/v1/organizations/{organization_id}/users/{user_id} | DELETE | remove_user_from_organization_api_v1_organizations__organization_id__users__user_id__delete | 将用户从组织移除 | 从组织中移除指定用户，需组织管理员或系统管理员权限。不可移除自己。 |

## external_admin

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/external/admin/users | POST | create_user_api_v1_external_admin_users_post | Create User | 创建用户（仅外部管理系统可访问） |
| /api/v1/external/admin/users | GET | get_users_api_v1_external_admin_users_get | Get Users | 获取用户列表（仅外部管理系统可访问） |
| /api/v1/external/admin/users/{user_id} | PUT | update_user_api_v1_external_admin_users__user_id__put | Update User | 更新用户信息（仅外部管理系统可访问） |
| /api/v1/external/admin/users/{user_id} | DELETE | delete_user_api_v1_external_admin_users__user_id__delete | Delete User | 删除用户（仅外部管理系统可访问） |
| /api/v1/external/admin/organizations | POST | create_organization_api_v1_external_admin_organizations_post | Create Organization | 创建组织（仅外部管理系统可访问） |
| /api/v1/external/admin/organizations | GET | get_organizations_api_v1_external_admin_organizations_get | Get Organizations | 获取组织列表（仅外部管理系统可访问） |
| /api/v1/external/admin/organizations/{organization_id} | PUT | update_organization_api_v1_external_admin_organizations__organization_id__put | Update Organization | 更新组织信息（仅外部管理系统可访问） |
| /api/v1/external/admin/organizations/{organization_id} | DELETE | delete_organization_api_v1_external_admin_organizations__organization_id__delete | Delete Organization | 删除组织（仅外部管理系统可访问） |
| /api/v1/external/admin/organizations/{organization_id}/users/{user_id} | POST | assign_user_to_organization_api_v1_external_admin_organizations__organization_id__users__user_id__post | Assign User To Organization | 分配用户到组织（仅外部管理系统可访问） |
| /api/v1/external/admin/organizations/{organization_id}/users/{user_id} | DELETE | remove_user_from_organization_api_v1_external_admin_organizations__organization_id__users__user_id__delete | Remove User From Organization | 从组织移除用户（仅外部管理系统可访问） |

## 未分类

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/models | GET | get_models_api_models_get | Get Models | 获取当前用户可访问的所有AI模型列表。

返回经过权限过滤的模型列表，包括模型ID、名称、标签和价格等信息。
模型按照配置的顺序排序，并根据用户权限进行过滤。

Args:
    request (Request): 请求上下文
    user (UserModel): 已认证的用户
    
Returns:
    dict: 包含过滤后的模型列表 |
| /api/models/base | GET | get_base_models_api_models_base_get | Get Base Models | 获取所有基础模型列表（仅管理员可访问）。

返回系统中所有可用的基础模型，不受用户权限限制。

Args:
    request (Request): 请求上下文
    user (UserModel): 已认证的管理员用户
    
Returns:
    dict: 包含所有基础模型的列表
    
Note:
    此接口仅限管理员访问 |
| /api/embeddings | POST | embeddings_api_embeddings_post | Embeddings | OpenAI兼容的文本嵌入接口。

该处理器:
  - 执行用户/模型检查并分发到正确的后端。
  - 支持OpenAI、Ollama、竞技场模型、管道和任何兼容的提供商。

Args:
    request (Request): 请求上下文。
    form_data (dict): OpenAI格式的负载 (例如: {"model": "...", "input": [...]})
    user (UserModel): 已认证的用户。

Returns:
    dict: OpenAI兼容的嵌入向量响应。 |
| /api/chat/completions | POST | chat_completion_api_chat_completions_post | Chat Completion | 聊天完成接口，处理AI对话请求。

该接口支持:
  - 多种模型类型(OpenAI、Ollama等)
  - 工具调用和函数调用
  - 文件上传和处理
  - 背景任务处理
  
Args:
    request (Request): 请求上下文
    form_data (dict): 包含模型ID、消息历史、参数等的请求体
    user (UserModel): 已认证的用户
    
Returns:
    dict: 包含AI生成内容的响应
    
Raises:
    HTTPException: 当积分不足、模型访问受限或处理失败时 |
| /api/chat/completed | POST | chat_completed_api_chat_completed_post | Chat Completed | 标记聊天会话为已完成状态。

在聊天完成后调用此接口，用于更新聊天状态、处理后续任务和清理资源。

Args:
    request (Request): 请求上下文
    form_data (dict): 包含聊天会话信息的请求体
    user (UserModel): 已认证的用户
    
Returns:
    dict: 操作结果
    
Raises:
    HTTPException: 当处理失败时 |
| /api/chat/actions/{action_id} | POST | chat_action_api_chat_actions__action_id__post | Chat Action | 执行聊天相关的特定动作。

根据action_id执行不同的聊天操作，如重新生成回复、继续生成等。

Args:
    request (Request): 请求上下文
    action_id (str): 要执行的动作ID
    form_data (dict): 包含动作参数的请求体
    user (UserModel): 已认证的用户
    
Returns:
    dict: 动作执行结果
    
Raises:
    HTTPException: 当动作执行失败时 |
| /api/tasks/stop/{task_id} | POST | stop_task_endpoint_api_tasks_stop__task_id__post | Stop Task Endpoint | 停止指定的后台任务。

Args:
    request (Request): 请求上下文
    task_id (str): 要停止的任务ID
    user (UserModel): 已认证的用户
    
Returns:
    dict: 包含停止操作结果的响应
    
Raises:
    HTTPException: 当任务不存在或无法停止时 |
| /api/tasks | GET | list_tasks_endpoint_api_tasks_get | List Tasks Endpoint | 列出所有当前运行的后台任务。

返回系统中所有正在运行的任务列表，包括任务ID、状态和相关信息。

Args:
    request (Request): 请求上下文
    user (UserModel): 已认证的用户
    
Returns:
    dict: 包含任务列表的响应 |
| /api/tasks/chat/{chat_id} | GET | list_tasks_by_chat_id_endpoint_api_tasks_chat__chat_id__get | List Tasks By Chat Id Endpoint | 获取指定聊天会话相关的所有任务ID。

Args:
    request (Request): 请求上下文
    chat_id (str): 聊天会话ID
    user (UserModel): 已认证的用户
    
Returns:
    dict: 包含与指定聊天相关的任务ID列表
    
Note:
    如果聊天不存在或不属于当前用户，将返回空列表 |
| /api/config | GET | get_app_config_api_config_get | Get App Config | 获取应用程序配置信息。

返回系统配置信息，包括功能开关、默认设置、OAuth提供商等。
根据用户是否登录返回不同级别的配置信息。

Args:
    request (Request): 请求上下文
    
Returns:
    dict: 包含应用配置的字典 |
| /api/webhook | GET | get_webhook_url_api_webhook_get | Get Webhook Url | 暂无描述 |
| /api/webhook | POST | update_webhook_url_api_webhook_post | Update Webhook Url | 暂无描述 |
| /api/version | GET | get_app_version_api_version_get | Get App Version | 暂无描述 |
| /api/version/updates | GET | get_app_latest_release_version_api_version_updates_get | Get App Latest Release Version | 暂无描述 |
| /api/changelog | GET | get_app_changelog_api_changelog_get | Get App Changelog | 暂无描述 |
| /api/usage | GET | get_current_usage_api_usage_get | Get Current Usage | 获取Open WebUI的当前使用统计信息。

返回当前活跃的模型ID列表和用户ID列表，用于监控系统负载和使用情况。
此接口为实验性功能，可能会在未来版本中变更。

Returns:
    dict: 包含活跃模型ID和用户ID的字典
    
Raises:
    HTTPException: 当获取统计信息失败时返回500错误 |
| /oauth/{provider}/login | GET | oauth_login_oauth__provider__login_get | Oauth Login | 暂无描述 |
| /oauth/{provider}/callback | GET | oauth_callback_oauth__provider__callback_get | Oauth Callback | 暂无描述 |
| /manifest.json | GET | get_manifest_json_manifest_json_get | Get Manifest Json | 暂无描述 |
| /opensearch.xml | GET | get_opensearch_xml_opensearch_xml_get | Get Opensearch Xml | 暂无描述 |
| /health | GET | healthcheck_health_get | Healthcheck | 健康检查接口。

用于监控系统是否正常运行，返回简单的状态指示。

Returns:
    dict: 包含状态标志的响应 |
| /health/db | GET | healthcheck_with_db_health_db_get | Healthcheck With Db | 数据库健康检查接口。

检查数据库连接是否正常，执行简单查询验证数据库可用性。

Returns:
    dict: 包含状态标志的响应
    
Raises:
    HTTPException: 当数据库连接失败时 |
| /cache/{path} | GET | serve_cache_file_cache__path__get | Serve Cache File | 暂无描述 |

