# Assumptions to confirm

1. Only the first opened cell must be in the interior. Border cells can be opened in steps 3 and 5.
2. "Cut by at least half" means stop once `2 * current_dead_ends <= N0`.
3. The button is an ordinary open cell and can burn. The trial then ends as `BUTTON_BURNED`.
4. The bot may stay in place.
5. The bot knows `q`.
6. If one fire step burns both the bot's cell and the button, the outcome is `BURNED`.
