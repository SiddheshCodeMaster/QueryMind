import pandas as pd


class JoinResolver:
    """
    Detects when a query's metric and dimension columns exist in different
    sheets (i.e. have no rows where both are non-null simultaneously),
    finds the join key automatically, and produces a merged DataFrame
    that the Analyzer can use normally.

    Domain-agnostic: works purely from the loaded data structure.
    No hardcoded column names or subject-matter assumptions.

    Context keys read
    -----------------
    intent              – {"metric": str, "dimension": str, ...}
    dataframe           – combined df (all sheets outer-joined)
    sheet_dataframes    – dict[sheet_name -> DataFrame]
    schema              – {"columns": [...]}

    Context keys written
    --------------------
    dataframe           – replaced with joined df when a join is needed
    schema              – updated to reflect joined df columns
    join_resolved       – True if a join was performed
    join_info           – dict with join details (for debugging / TUI display)
    """

    def run(self, context: dict) -> dict:
        sheet_dfs = context.get("sheet_dataframes", {})

        # Only relevant for multi-sheet Excel files
        if len(sheet_dfs) < 2:
            return context

        intent = context.get("intent", {})
        metric = intent.get("metric")
        dimension = intent.get("dimension")

        if not metric or not dimension:
            return context

        combined = context["dataframe"]

        # ── Co-existence check ────────────────────────────────────────────
        # The combined df outer-joins all sheets, so both columns may exist
        # but have non-null values on completely different rows.
        # If there are no rows where BOTH are non-null → cross-sheet join needed.
        if metric in combined.columns and dimension in combined.columns:
            both_valid = (combined[metric].notna() & combined[dimension].notna()).sum()
            if both_valid > 0:
                return context  # columns co-exist — no join needed

        # ── Find which sheet owns each column ─────────────────────────────
        metric_sheet = self._find_sheet(metric, sheet_dfs)
        dimension_sheet = self._find_sheet(dimension, sheet_dfs)

        if not metric_sheet:
            return context  # let Analyzer produce a clear column-not-found error

        if not dimension_sheet:
            return context  # same

        if metric_sheet == dimension_sheet:
            # Both happen to be in the same sheet — use that df directly
            context["dataframe"] = sheet_dfs[metric_sheet].copy()
            context["schema"] = self._build_schema(context["dataframe"])
            return context

        # ── Find join key ─────────────────────────────────────────────────
        join_key = self._find_join_key(
            sheet_dfs[metric_sheet],
            sheet_dfs[dimension_sheet],
        )

        if not join_key:
            context["error"] = (
                f"Cannot answer this query automatically.\n\n"
                f"  '{metric}' lives in '{metric_sheet}' and "
                f"'{dimension}' lives in '{dimension_sheet}', "
                f"but these sheets share no common column to join on.\n\n"
                f"  Try a query within a single sheet instead."
            )
            return context

        # ── Perform the join ──────────────────────────────────────────────
        try:
            left_df = sheet_dfs[metric_sheet].copy()
            right_df = sheet_dfs[dimension_sheet].copy()

            # Only bring new columns from right (avoids _x/_y suffix collisions)
            new_cols = [join_key] + [
                c for c in right_df.columns if c not in left_df.columns
            ]
            right_df = right_df[new_cols]

            joined = left_df.merge(right_df, on=join_key, how="left")

            context["dataframe"] = joined
            context["schema"] = self._build_schema(joined)
            context["join_resolved"] = True
            context["join_info"] = {
                "metric_sheet": metric_sheet,
                "dimension_sheet": dimension_sheet,
                "join_key": join_key,
                "joined_shape": joined.shape,
            }

            print(
                f"JoinResolver: '{metric_sheet}' ⋈ '{dimension_sheet}' "
                f"ON '{join_key}' → {joined.shape}"
            )

        except Exception as e:
            context["error"] = f"Join failed: {e}"

        return context

    # ── Helpers ───────────────────────────────────────────────────────────

    def _find_sheet(self, column: str, sheet_dfs: dict):
        """Return the first sheet that contains column."""
        for sheet, df in sheet_dfs.items():
            if column in df.columns:
                return sheet
        return None

    def _find_join_key(
        self,
        left_df: pd.DataFrame,
        right_df: pd.DataFrame,
    ):
        """
        Find the best shared column to join on.

        Scoring: prefer columns where the right sheet is more lookup-like
        (few unique values on right, many on left = classic FK→PK join).
        Exclude obvious row-number columns.
        """
        shared = set(left_df.columns) & set(right_df.columns)

        excluded_hints = {"row_id", "index", "unnamed"}
        shared = {c for c in shared if not any(h in c.lower() for h in excluded_hints)}

        if not shared:
            return None

        def score(col):
            try:
                return right_df[col].nunique() / max(left_df[col].nunique(), 1)
            except Exception:
                return 1.0

        return sorted(shared, key=score)[0]

    def _build_schema(self, df: pd.DataFrame) -> dict:
        return {
            "columns": [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
        }
