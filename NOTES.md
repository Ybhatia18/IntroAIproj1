# Assumptions to confirm

1. Only the first opened cell must be in the interior. Border cells can be opened in steps 3 and 5.
2. "Cut by at least half" means stop once `2 * current_dead_ends <= N0`.
3. The button is an ordinary open cell and can burn. The trial then ends as `BUTTON_BURNED`.
4. The bot may stay in place.
5. The bot knows `q`.
6. If one fire step burns both the bot's cell and the button, the outcome is `BURNED`.
7. When a bot has no path to the button, it gives up (`GAVE_UP`). Fire never goes out, so once every route is blocked, none will open again.
8. Bot 3's buffer applies to the button too. If the button is next to the fire, Bot 3 falls back to Bot 2's plan.
9. BFS checks neighbors in a fixed order (up, down, left, right), so ties between equal-length paths are broken the same way for every bot.
10. Bot 4's risk model treats neighbors as "maybe burning": a cell catches with chance 1 - prod(1 - q * p_neighbor). That's exactly 1 - (1 - q)^K for the first step, but it ignores correlations between cells after that.
11. Bot 4's FE!N Mode is permanent: once it decides to run, it doesn't go back to careful routing.
