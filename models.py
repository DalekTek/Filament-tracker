from dataclasses import dataclass
from datetime import datetime

@dataclass
class Filament:
    id: int
    name: str
    material_type: str
    initial_weight: float
    current_weight: float
    color: str
    created_at: datetime
    updated_at: datetime

    @property
    def remaining_percentage(self) -> float:
        return (self.current_weight / self.initial_weight) * 100

    def __str__(self) -> str:
        return (
            f"Катушка: {self.name}\n"
            f"Материал: {self.material_type}\n"
            f"Цвет: {self.color}\n"
            f"Начальный вес: {self.initial_weight}г\n"
            f"Текущий вес: {self.current_weight}г\n"
            f"Осталось: {self.remaining_percentage:.1f}%"
        )