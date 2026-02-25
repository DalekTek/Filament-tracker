from aiogram import Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import Database


class FilamentStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_material = State()
    waiting_for_material = State()
    waiting_for_weight = State()
    waiting_for_color = State()
    waiting_for_new_weight = State()


class FilamentHandler:
    def __init__(self, database: Database):
        self.db = database
        self.dp = None

    def register_handlers(self, dp: Dispatcher) -> None:
        self.dp = dp

        # Регистрация обработчиков команд
        dp.message.register(self.cmd_start, Command("start"))
        dp.message.register(self.cmd_help, Command("help"))
        dp.message.register(self.cmd_add, Command("add"))
        dp.message.register(self.cmd_list, Command("list"))
        dp.message.register(self.cmd_update, Command("update"))

        # Регистрация обработчиков состояний
        dp.message.register(self.process_name, StateFilter(FilamentStates.waiting_for_name))
        dp.message.register(self.process_material, StateFilter(FilamentStates.waiting_for_material))
        dp.message.register(self.process_weight, StateFilter(FilamentStates.waiting_for_weight))
        dp.message.register(self.process_color, StateFilter(FilamentStates.waiting_for_color))
        dp.message.register(self.process_new_weight, StateFilter(FilamentStates.waiting_for_new_weight))

    async def handle_message(self, message: types.Message) -> None:
        """
        Основной метод обработки сообщений
        :param message: Входящее сообщение
        """
        # Получаем контекст FSM для всех операций
        state = self.dp.fsm.get_context(message.bot, message.chat.id, message.from_user.id)

        command = message.text.split()[0] if message.text else None
        if command and command.startswith('/'):
            if command == '/start':
                await self.cmd_start(message)
            elif command == '/help':
                await self.cmd_help(message)
            elif command == '/add':
                await self.cmd_add(message, state)
            elif command == '/list':
                await self.cmd_list(message)
            elif command.startswith('/update'):
                await self.cmd_update(message, state)
            else:
                await message.answer("Неизвестная команда. Используйте /help для просмотра доступных команд.")
        else:
            # Обработка сообщений в состояниях
            current_state = await state.get_state()
            if current_state == FilamentStates.waiting_for_name:
                await self.process_name(message, state)
            elif current_state == FilamentStates.waiting_for_material:
                await self.process_material(message, state)
            elif current_state == FilamentStates.waiting_for_weight:
                await self.process_weight(message, state)
            elif current_state == FilamentStates.waiting_for_color:
                await self.process_color(message, state)
            elif current_state == FilamentStates.waiting_for_new_weight:
                await self.process_new_weight(message, state)
            else:
                await message.answer("Используйте команды для взаимодействия с ботом. /help для справки.")

    async def cmd_start(self, message: types.Message) -> None:
        await message.answer(
            "Привет! Я бот для отслеживания пластика в катушках.\n"
            "Используйте /help для просмотра доступных команд."
        )

    async def cmd_help(self, message: types.Message) -> None:
        help_text = (
            "Доступные команды:\n"
            "/add - Добавить новую катушку\n"
            "/list - Показать все катушки\n"
            "/update <id> - Обновить вес катушки\n"
            "/help - Показать это сообщение"
        )
        await message.answer(help_text)

    async def cmd_add(self, message: types.Message, state: FSMContext) -> None:
        await state.set_state(FilamentStates.waiting_for_name)
        await message.answer("Введите название катушки:")

    async def process_name(self, message: types.Message, state: FSMContext) -> None:
        await state.update_data(name=message.text)
        await state.set_state(FilamentStates.waiting_for_material)
        await message.answer("Введите тип материала (PLA, PETG, ABS и т.д.):")

    async def process_material(self, message: types.Message, state: FSMContext) -> None:
        await state.update_data(material=message.text)
        await state.set_state(FilamentStates.waiting_for_weight)
        await message.answer("Введите начальный вес катушки в граммах:")

    async def process_weight(self, message: types.Message, state: FSMContext) -> None:
        try:
            weight = float(message.text)
            await state.update_data(weight=weight)
            await state.set_state(FilamentStates.waiting_for_color)
            await message.answer("Введите цвет пластика:")
        except ValueError:
            await message.answer("Пожалуйста, введите корректное числовое значение.")

    async def process_color(self, message: types.Message, state: FSMContext) -> None:
        data = await state.get_data()
        filament_id = await self.db.add_filament(
            name=data['name'],
            material_type=data['material'].upper(),
            initial_weight=data['weight'],
            color=message.text.lower()
        )
        await state.clear()
        await message.answer(f"Катушка успешно добавлена! ID: {filament_id}")

    async def cmd_list(self, message: types.Message) -> None:
        filaments = await self.db.get_all_filaments()
        if not filaments:
            await message.answer("Список катушек пуст.")
            return

        response_parts = ["Список катушек:\n"]
        for filament in filaments:
            response_parts.append(
                f"ID: {filament.id}\n"
                f"Название: {filament.name}\n"
                f"Материал: {filament.material_type}\n"
                f"Цвет: {filament.color}\n"
                f"Начальный вес: {filament.initial_weight}г\n"
                f"Текущий вес: {filament.current_weight}г\n"
                f"Осталось: {filament.remaining_percentage:.1f}%\n"
            )

        # Отправляем сообщения частями, если они слишком длинные
        current_message = ""
        for part in response_parts:
            if len(current_message) + len(part) > 4000:
                await message.answer(current_message)
                current_message = part
            else:
                current_message += "\n" + part

        if current_message:
            await message.answer(current_message)

    async def cmd_update(self, message: types.Message, state: FSMContext) -> None:
        try:
            filament_id = int(message.text.split()[1])
            filament = await self.db.get_filament(filament_id)
            if not filament:
                await message.answer("Катушка с таким ID не найдена.")
                return

            await state.update_data(filament_id=filament_id)
            await state.set_state(FilamentStates.waiting_for_new_weight)
            await message.answer(
                f"Текущие данные катушки:\n"
                f"Название: {filament.name}\n"
                f"Текущий вес: {filament.current_weight}г\n"
                f"Введите новый вес:"
            )
        except (IndexError, ValueError):
            await message.answer("Используйте формат: /update <id>")

    async def process_new_weight(self, message: types.Message, state: FSMContext) -> None:
        try:
            new_weight = float(message.text)
            data = await state.get_data()
            filament_id = data['filament_id']

            if await self.db.update_weight(filament_id, new_weight):
                filament = await self.db.get_filament(filament_id)
                await message.answer(
                    f"Вес обновлен!\n\n"
                    f"Название: {filament.name}\n"
                    f"Новый вес: {filament.current_weight}г\n"
                    f"Осталось: {filament.remaining_percentage:.1f}%"
                )
            else:
                await message.answer("Ошибка при обновлении веса.")

            await state.clear()
        except ValueError:
            await message.answer("Пожалуйста, введите корректное числовое значение.")