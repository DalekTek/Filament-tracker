%% ============================================
%% МЕРМАЙД-ДИАГРАММА: SecureFilamentBot Architecture
%% Сгенерировано на основе Итоговой Архитектуры
%% ============================================

%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ffdfd3', 'edgeLabelBackground':'#f9f7f7', 'tertiaryColor': '#dcdcdc', 'fontFamily': 'monospace', 'lineColor': '#4a4a4a'}}}%%
flowchart TD
    %% ============================================
    %% ЭТАП 1: ОПРЕДЕЛЕНИЕ БЛОКОВ И ПОДГРАФОВ (DRY)
    %% ============================================
    
    %% 🌐 Внешние системы и инфраструктура
    subgraph External["🌐 Внешние системы и инфраструктура"]
        Telegram["Telegram API<br/>Long Polling / Updates"]
        Redis[("💾 Redis Queue<br/>redis://host:port")]
        DB[("🗄️ Database<br/>SQLite/PostgreSQL")]
    end
    
    %% 🚀 Точка входа в приложение
    subgraph Entry["🚀 Точка входа"]
        Main["main()<br/>• logging.basicConfig()<br/>• bot = SecureFilamentBot()<br/>• asyncio.run(bot.start())"]
    end
    
    %% 🎛️ Оркестратор: SecureFilamentBot
    subgraph Orchestrator["🎛️ Orchestrator: SecureFilamentBot"]
        BotInit["__init__()<br/>• logger, config<br/>• Bot, Dispatcher, MemoryStorage<br/>• SecurityManager, QueueManager<br/>• Database, FilamentHandler"]
        
        %% 📨 Конвейер обработки сообщений
        subgraph MessagePipeline["📨 Message Processing Pipeline"]
            ValidateSession["🔐 validate_session(user_id)<br/>Проверка/создание сессии"]
            CreateQueueMsg["📦 Create QueueMessage DTO<br/>• user_id, text, command<br/>• timestamp, metadata{chat_id, msg_id}"]
            PushQueue["⬇️ queue.push_message()<br/>Асинхронная отправка в Redis"]
            EncryptLog["🔒 Security: encrypt + hash<br/>для безопасного аудита"]
            LogInfo["📝 logger.info()<br/>'Received from {user_id}<br/>Hash: {message_hash}'"]
            CheckAdmin["🛡️ is_admin(user_id) check<br/>для команд: /admin, /stats, /debug"]
            DenyAccess["❌ message.answer()<br/>'У вас нет прав...'"]
            CallHandler["⚡ handler.handle_message()<br/>Делегирование бизнес-логике"]
        end
        
        %% 🔄 Фоновая задача обработки очереди
        subgraph BackgroundTask["🔄 Background: process_queue()"]
            QueueLoop["♾️ while True loop<br/>• await queue.get_message()<br/>• Process logic here<br/>• asyncio.sleep(1)<br/>• Exception handling"]
        end
        
        %% 🔄 Методы жизненного цикла
        subgraph Lifecycle["🔄 Lifecycle Management"]
            StartMethod["▶️ start()<br/>• await queue.connect()<br/>• await db.create_tables()<br/>• handler.register_handlers(dp)<br/>• dp.message.middleware()<<br/>• asyncio.create_task(queue)<br/>• dp.start_polling()"]
            CleanupMethod["⏹️ cleanup()<br/>• Cancel queue_task<br/>• await queue.close()<br/>• await bot.session.close()<br/>• await storage.close()"]
        end
    end
    
    %% ⚙️ Middleware слой
    subgraph Middleware["⚙️ Middleware Layer"]
        MsgMiddleware["MessageMiddleware<br/>__call__(handler, event, data)<br/>→ await bot.process_message(event)"]
    end
    
    %% 💼 Бизнес-логика
    subgraph BusinessLogic["💼 Business Logic Layer"]
        FilamentHandler["FilamentHandler<br/>handle_message(Message)<br/>Core domain logic<br/>Command routing & execution"]
    end
    
    %% 🚨 Обработчики ошибок
    subgraph ErrorHandling["🚨 Error Handling"]
        LogError["🚨 logger.error()<br/>'Error processing message: {e}'"]
        UserErrorNotify["⚠️ message.answer()<br/>'Произошла ошибка...'"]
        QueueError["🚨 logger.error()<br/>'Queue processing error: {e}'"]
    end
    
    %% ============================================
    %% ЭТАП 2: ОПРЕДЕЛЕНИЕ СВЯЗЕЙ (LINKS)
    %% ============================================
    
    %% === Точка входа → Инициализация ===
    Main -->|"1. asyncio.run()"| StartMethod
    StartMethod -->|"2. Инициализация компонентов"| BotInit
    
    %% === Поток входящего сообщения ===
    Telegram -->|"incoming update"| MsgMiddleware
    MsgMiddleware -->|"3. Delegate to bot"| ValidateSession
    
    %% === Конвейер обработки: последовательные шаги ===
    ValidateSession -->|"4. Session OK"| CreateQueueMsg
    CreateQueueMsg -->|"5. DTO ready"| PushQueue
    PushQueue -->|"6. Async push"| Redis
    PushQueue -->|"7. Parallel: security"| EncryptLog
    EncryptLog -->|"8. Encrypted + hashed"| LogInfo
    LogInfo -->|"9. Audit logged"| CheckAdmin
    
    %% === Ветвление: проверка прав администратора ===
    CheckAdmin -->|"10. Command check"| IsAdminCheck{"Command in<br/>['/admin', '/stats', '/debug']?"}
    IsAdminCheck -->|"Yes + ¬is_admin()"| DenyAccess
    DenyAccess -->|"11. Return early"| Telegram
    IsAdminCheck -->|"No command OR is_admin()=True"| CallHandler
    
    %% === Делегирование бизнес-логике ===
    CallHandler -->|"12. Execute domain logic"| FilamentHandler
    FilamentHandler -->|"13. Send response"| Telegram
    
    %% === Фоновая обработка очереди ===
    Redis -->|"pop message"| QueueLoop
    QueueLoop -->|"14. Process queued item"| BusinessLogic
    QueueLoop -->|"continue loop"| QueueLoop
    
    %% === Управление жизненным циклом ===
    BotInit -->|"components initialized"| StartMethod
    StartMethod -->|"15. Start polling"| Telegram
    StartMethod -->|"16. Create background task"| BackgroundTask
    
    %% === Корректное завершение работы ===
    Main -->|"KeyboardInterrupt / SystemExit"| CleanupMethod
    CleanupMethod -->|"17. Close connections"| Redis
    CleanupMethod -->|"18. Close DB"| DB
    CleanupMethod -->|"19. Cleanup session"| Telegram
    
    %% === Обработка ошибок: основной конвейер ===
    MessagePipeline -.->|"Exception caught"| LogError
    LogError -->|"20. Notify user"| UserErrorNotify
    UserErrorNotify --> Telegram
    
    %% === Обработка ошибок: фоновая задача ===
    QueueLoop -.->|"Exception in queue"| QueueError
    QueueError -->|"21. Log + continue"| QueueLoop
    
    %% ============================================
    %% ЭТАП 3: ПРИМЕНЕНИЕ СТИЛЕЙ (STYLES)
    %% ============================================
    
    %% 🌐 Стили внешних систем
    style External fill:#e8f4f8,stroke:#2c7a7b,stroke-width:2px
    style Telegram fill:#fff3cd,stroke:#856404,stroke-width:1px
    style Redis fill:#d1ecf1,stroke:#0c5460,stroke-width:1px
    style DB fill:#d1ecf1,stroke:#0c5460,stroke-width:1px
    
    %% 🚀 Стили точки входа
    style Entry fill:#f8f9fa,stroke:#6c757d,stroke-width:2px
    style Main fill:#e2e3e5,stroke:#383d41,stroke-width:1px
    
    %% 🎛️ Стили оркестратора
    style Orchestrator fill:#fff3cd,stroke:#856404,stroke-width:2px
    style BotInit fill:#ffeeba,stroke:#856404,stroke-width:1px
    
    %% 📨 Стили конвейера сообщений
    style MessagePipeline fill:#d4edda,stroke:#155724,stroke-width:1px
    style ValidateSession fill:#c3e6cb,stroke:#155724
    style CreateQueueMsg fill:#c3e6cb,stroke:#155724
    style PushQueue fill:#c3e6cb,stroke:#155724
    style EncryptLog fill:#c3e6cb,stroke:#155724
    style LogInfo fill:#c3e6cb,stroke:#155724
    style CheckAdmin fill:#c3e6cb,stroke:#155724
    style DenyAccess fill:#f8d7da,stroke:#721c24
    style CallHandler fill:#c3e6cb,stroke:#155724
    
    %% 🔄 Стили фоновой задачи
    style BackgroundTask fill:#cce5ff,stroke:#004085,stroke-width:1px
    style QueueLoop fill:#b8daff,stroke:#004085
    
    %% 🔄 Стили жизненного цикла
    style Lifecycle fill:#e2e3e5,stroke:#383d41,stroke-width:1px
    style StartMethod fill:#d6d8db,stroke:#383d41
    style CleanupMethod fill:#d6d8db,stroke:#383d41
    
    %% ⚙️ Стили middleware
    style Middleware fill:#f5c6cb,stroke:#721c24,stroke-width:2px
    style MsgMiddleware fill:#f8d7da,stroke:#721c24
    
    %% 💼 Стили бизнес-логики
    style BusinessLogic fill:#d1ecf1,stroke:#0c5460,stroke-width:2px
    style FilamentHandler fill:#bee5eb,stroke:#0c5460
    
    %% 🚨 Стили обработки ошибок
    style ErrorHandling fill:#f8d7da,stroke:#721c24,stroke-width:1px
    style LogError fill:#f5c6cb,stroke:#721c24
    style UserErrorNotify fill:#f5c6cb,stroke:#721c24
    style QueueError fill:#f5c6cb,stroke:#721c24
    
    %% 🔀 Стили узлов-решений
    style IsAdminCheck fill:#fff3cd,stroke:#856404,stroke-width:2px,stroke-dasharray:5 5
    
    %% ============================================
    %% ПРИМЕЧАНИЯ ПО АРХИТЕКТУРЕ (комментарии)
    %% ============================================
    %% • Архитектура: Layered Event-Driven с Async Processing
    %% • Безопасность: Session validation → Encryption → AuthZ → Audit logging
    %% • Масштабируемость: QueueManager выносит обработку в Redis
    %% • Отказоустойчивость: Graceful shutdown + try/except на каждом уровне
    %% • Тестируемость: Возможность внедрения mock-зависимостей через DI (рекомендация)
    %% • Потенциальные улучшения: 
    %%   - Выделить QueueConsumer в отдельный сервис
    %%   - Добавить health-checks и метрики
    %%   - Использовать dependency injection для слабой связности