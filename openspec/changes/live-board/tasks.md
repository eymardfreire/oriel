## 1. Weather payload

- [x] 1.1 Add apparent temperature, humidity, and wind to the existing Open-Meteo observation parse and item fields
- [x] 1.2 Cover the new fields in the weather tests, including omission when the source omits them

## 2. Night theme and live rows

- [x] 2.1 Retune the night palette and update the hex test
- [x] 2.2 Draw weather glyphs and extra observation numbers only from payload fields
- [x] 2.3 Draw a quote magnitude bar from the change, and tick relative ages plus a live mark

## 3. Board, density, and settings

- [x] 3.1 Place panels in one to four columns from the terminal width, including a single bay
- [x] 3.2 Add a status line, focus with j and k, theme cycle, and a settings overlay
- [x] 3.3 Add board mode that fetches the selected bays and remembers the selection
- [x] 3.4 Rewrite the suggestion line so it names the desk, the reason, and the apply key

## 4. Check

- [x] 4.1 Run the server weather tests and the Go client tests
