"""
Лабораторна робота № 10.
Комплексний конвеєр файлового введення-виведення: обробка CSV,
бінарна верифікація сигнатур та персистентна серіалізація у JSON.
Варіант 1: Телеметрія сонячної електростанції (solar.csv, сигнатура 0x534F4C52).
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

# Константа 4-байтної магічної сигнатури бінарного образу для Варіанта 1 ("SOLR")
FIRMWARE_MAGIC_HEADER = bytes([0x53, 0x4F, 0x4C, 0x52])


def process_csv_telemetry(input_csv_path: Path, output_csv_path: Path) -> dict:
    """
    Зчитує дані телеметрії сонячної електростанції через csv.DictReader,
    фільтрує записи за критерієм напруги > 220 В, обчислює потужність P = U * I
    та записує відібрані дані у новий CSV-файл через csv.DictWriter.
    """
    if not input_csv_path.exists():
        raise FileNotFoundError(f"Вхідний файл '{input_csv_path}' не знайдено.")

    total_records = 0
    valid_records = 0
    total_power_watts = 0.0
    cleaned_rows = []

    with open(input_csv_path, mode="r", encoding="utf-8") as in_file:
        reader = csv.DictReader(in_file)

        for row in reader:
            total_records += 1
            voltage = float(row["Voltage_V"])
            current = float(row["Current_A"])
            freq = float(row["Frequency_Hz"])

            # Критерій Варіанта 1: напруга > 220 В; розрахунок потужності P = U * I
            if voltage > 220.0:
                valid_records += 1
                power_w = voltage * current
                total_power_watts += power_w

                cleaned_rows.append({
                    "Timestamp": row["Timestamp"],
                    "Voltage_V": f"{voltage:.2f}",
                    "Current_A": f"{current:.2f}",
                    "Power_W": f"{power_w:.2f}",
                    "Frequency_Hz": f"{freq:.2f}"
                })

    if cleaned_rows:
        fieldnames = ["Timestamp", "Voltage_V", "Current_A", "Power_W", "Frequency_Hz"]
        with open(output_csv_path, mode="w", encoding="utf-8", newline="") as out_file:
            writer = csv.DictWriter(out_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cleaned_rows)

    avg_power = (total_power_watts / valid_records) if valid_records > 0 else 0.0

    return {
        "total_read_rows": total_records,
        "valid_saved_rows": valid_records,
        "filtered_out_rows": total_records - valid_records,
        "average_power_watts": avg_power,
        "total_power_watts": total_power_watts,
        "total_active_power_kw": total_power_watts / 1000.0
    }


def verify_binary_firmware(bin_path: Path) -> dict:
    """
    Здійснює низькорівневий аналіз бінарного образу прошивки:
    перевіряє магічну сигнатуру, позиціонує курсор та вилучає версію.
    """
    if not bin_path.exists():
        raise FileNotFoundError(f"Файл бінарного образу '{bin_path}' не знайдено.")

    with open(bin_path, mode="rb") as b_file:
        header = b_file.read(4)
        if header != FIRMWARE_MAGIC_HEADER:
            raise ValueError(
                f"Невідомий формат образу: сигнатура {header.hex().upper()} != {FIRMWARE_MAGIC_HEADER.hex().upper()}"
            )

        major_ver = int(b_file.read(1)[0])
        minor_ver = int(b_file.read(1)[0])

        current_pos = b_file.tell()
        file_size_bytes = b_file.seek(0, os.SEEK_END)
        payload_size = file_size_bytes - current_pos

    return {
        "magic_signature_hex": f"0x{header.hex().upper()}",
        "firmware_version": f"v{major_ver}.{minor_ver}",
        "total_image_size_bytes": file_size_bytes,
        "payload_size_bytes": payload_size,
        "is_signature_valid": True
    }


def export_system_snapshot(output_json_path: Path, csv_stats: dict, bin_stats: dict) -> None:
    """
    Серіалізує підсумковий стан системи у структурований JSON-документ.
    """
    snapshot_payload = {
        "station_metadata": {
            "facility_name": "Solar Power Plant Telemetry (Variant 1)",
            "snapshot_generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pipeline_version": "1.0.0"
        },
        "solar_telemetry_summary": csv_stats,
        "controller_firmware_audit": bin_stats
    }

    with open(output_json_path, mode="w", encoding="utf-8") as j_file:
        json.dump(snapshot_payload, j_file, indent=4, ensure_ascii=False)


def main() -> None:
    """Головна точка входу лабораторної роботи."""
    print("=" * 80)
    print(f"{'КОНВЕЄР ФАЙЛОВОГО ВВЕДЕННЯ-ВИВЕДЕННЯ ТА ЗБЕРЕЖЕННЯ СТАНУ':^80}")
    print("=" * 80)

    input_csv = Path("solar.csv")
    cleaned_csv = Path("cleaned_solar.csv")
    input_bin = Path("firmware_sample.bin")
    output_json = Path("solar_snapshot.json")

    t_start = time.perf_counter()

    csv_metrics = process_csv_telemetry(input_csv, cleaned_csv)
    print("Обробка CSV успішна:")
    print(f"  Зчитано рядків:      {csv_metrics['total_read_rows']:>5d}")
    print(f"  Валідних рядків:     {csv_metrics['valid_saved_rows']:>5d}")
    print(f"  Відсіяно за умовою:  {csv_metrics['filtered_out_rows']:>5d}")
    print(f"  Сумарна потужність:  {csv_metrics['total_power_watts']:>8.2f} Вт")
    print(f"  Середня потужність:  {csv_metrics['average_power_watts']:>8.2f} Вт")
    print(f"  Файл збережено:      {cleaned_csv.name}")
    print("-" * 80)

    bin_metrics = verify_binary_firmware(input_bin)
    print("Аудит бінарного образу успішний:")
    print(f"  Магічна сигнатура:   {bin_metrics['magic_signature_hex']}")
    print(f"  Версія прошивки:     {bin_metrics['firmware_version']}")
    print(f"  Загальний розмір:    {bin_metrics['total_image_size_bytes']} байтів")
    print(f"  Розмір корисних даних:{bin_metrics['payload_size_bytes']} байтів")
    print("-" * 80)

    export_system_snapshot(output_json, csv_metrics, bin_metrics)
    print("Підсумковий знімок стану збережено у JSON:")
    print(f"  Цільовий файл:       {output_json.name}")
    print("=" * 80)

    t_elapsed = time.perf_counter() - t_start
    print(f"Час виконання повного конвеєра: {t_elapsed * 1000:.3f} мс\n")


if __name__ == "__main__":
    main()