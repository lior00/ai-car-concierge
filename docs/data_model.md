# Data Model — inventory.db

## Table: `inventory`

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER | NOT NULL | Primary key, auto-increment |
| `make` | TEXT | NOT NULL | Vehicle manufacturer (e.g., "BMW", "Tesla") |
| `model` | TEXT | NOT NULL | Vehicle model name (e.g., "3 Series", "Model Y") |
| `year` | INTEGER | NOT NULL | Model year — **critical for policy enforcement** |
| `trim` | TEXT | YES | Trim level (e.g., "xDrive40i", "Long Range") |
| `color` | TEXT | YES | Exterior color |
| `fuel_type` | TEXT | NOT NULL | `'Electric'`, `'Gasoline'`, or `'Hybrid'` |
| `transmission` | TEXT | YES | `'Automatic'` or `'Manual'` |
| `mileage` | INTEGER | YES | Odometer reading in miles (default 0) |
| `price` | REAL | NOT NULL | Listed price in USD |
| `stock_count` | INTEGER | NOT NULL | Units available (default 1). Decremented on reservation. |
| `vin` | TEXT | YES | Vehicle Identification Number (unique) |
| `description` | TEXT | YES | Short marketing description |

## Key Constraints

- `id` is the canonical vehicle identifier for automation tools
- `stock_count >= 0` must be enforced before reservation; never decrement below 0
- `year` is the source of truth for `policy_guard.enforce()` — never derive year from VIN
- `vin` is unique across all vehicles
- `fuel_type` values are an enum: only `'Electric'`, `'Gasoline'`, `'Hybrid'` are valid

## Policy Segmentation

| Year Range | Status | Action |
|---|---|---|
| 2019–2021 | Pending De-listing | Display only when directly queried; explain cannot sell |
| 2022–2025 | Sellable | Normal sale, reservation, test drive flow |

## Useful Query Patterns

```sql
-- All sellable inventory
SELECT * FROM inventory WHERE year >= 2022 AND stock_count > 0;

-- All EVs in stock
SELECT * FROM inventory WHERE fuel_type = 'Electric' AND year >= 2022 AND stock_count > 0;

-- Price range filter
SELECT * FROM inventory WHERE price BETWEEN 50000 AND 100000 AND year >= 2022;

-- Specific make search
SELECT * FROM inventory WHERE LOWER(make) = LOWER('BMW') AND year >= 2022;

-- Decrement stock on reservation
UPDATE inventory SET stock_count = stock_count - 1 WHERE id = ? AND stock_count > 0;
```

## Counts (as of initial migration)

| Year Range | Count |
|---|---|
| 2019 | 5 |
| 2020 | 7 |
| 2021 | 8 |
| 2022 | 20 |
| 2023 | 20 |
| 2024 | 20 |
| 2025 | 20 |
| **Total** | **100** |
