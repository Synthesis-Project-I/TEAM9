import pandas as pd


class TaskAssignmentCSP:
    """
    This class acts as the 'Decision Engine' that connects HR Data (translators_df),
    CRM Data (df3 / clients), and Historical Data (df1) to find the perfect match
    using hard constraints, schedule parsing, and automatic constraint relaxation.
    """
    def __init__(self, translators_df):
        self.translators_df = translators_df.copy()

    def build_client_requirements(self, company_name, clients_df, historical_df, task_date, task_deadline=None, task_start_time=None, task_end_time=None, task_length_hours=0, language_pair=None, task_type="Translation", followed_by=None, previous_translator_experience=0.0):
        client_data = clients_df[clients_df["CLIENT_NAME"] == company_name]
        if client_data.empty:
            return None

        max_rate = client_data["SELLING_HOURLY_PRICE"].iloc[0]
        min_quality = client_data["MIN_QUALITY"].iloc[0]
        min_on_time = client_data["MIN_ON_TIME_SCORE"].iloc[0] if "MIN_ON_TIME_SCORE" in client_data.columns else 0.0
        wildcard = str(client_data["WILDCARD"].iloc[0]).strip().lower() if "WILDCARD" in client_data.columns else "balanced"

        company_history = historical_df[historical_df["MANUFACTURER"] == company_name]
        if company_history.empty:
            subindustries, industries, groups = [], [], []
        else:
            subindustries = [str(x).strip() for x in company_history["MANUFACTURER_SUBINDUSTRY"].dropna().unique()]
            industries = [str(x).strip() for x in company_history["MANUFACTURER_INDUSTRY"].dropna().unique()]
            groups = [str(x).strip() for x in company_history["MANUFACTURER_INDUSTRY_GROUP"].dropna().unique()]

        try:
            start_dt = pd.to_datetime(task_date)
            end_dt = pd.to_datetime(task_deadline)
            window_days = max(1, (end_dt - start_dt).days + 1)
        except Exception:
            window_days = 1

        task_reqs = {
            "language_pair": language_pair,
            "task_date": task_date,
            "task_deadline": task_deadline,
            "task_start_time": task_start_time,
            "task_end_time": task_end_time,
            "task_length_hours": task_length_hours,
            "window_days": window_days,
            "max_hourly_rate": max_rate,
            "min_quality": min_quality,
            "min_on_time_score": min_on_time,
            "wildcard": wildcard,
            "task_type": task_type,
            "followed_by": followed_by,
            "previous_translator_experience": previous_translator_experience,
            "required_subindustry": subindustries,
            "required_industry": industries,
            "required_industry_group": groups,
            "min_subindustry_experience": 1.0,
            "min_industry_experience": 1.0,
            "min_industry_group_experience": 1.0,
        }

        print(f"\n--- AUTO-LOADED PROFILE FOR: {company_name} ---")
        print(f">> Task Effort: {task_length_hours:.2f} hours of work")
        print(f">> Project Window: {window_days} days to deliver")

        return task_reqs

    def diagnose_bottleneck(self, task_reqs):
        """
        THE DIAGNOSTIC TOOL: This applies constraints one by one to print EXACTLY which rule
        eliminates candidates. It is used when the system returns a Fatal Error, allowing
        Project Managers to see why staffing failed.
        """
        print("\n--- CSP BOTTLENECK DIAGNOSTIC ---")
        domain = self.translators_df.copy()

        pair = task_reqs.get("language_pair")
        if pair not in domain.columns:
            print(f"FAILED: Nobody speaks {pair}.")
            return

        domain = domain[domain[pair].notna()]
        print(f"Language ({pair}): {len(domain)} translators available.")
        if domain.empty:
            return

        if "max_hourly_rate" in task_reqs:
            domain = domain[domain[pair] <= task_reqs["max_hourly_rate"]]
            print(f"Budget (<= ${task_reqs['max_hourly_rate']}): {len(domain)} translators left.")
            if domain.empty:
                return

        if "min_quality" in task_reqs:
            domain = domain[domain["AVERAGE_QUALITY"] >= task_reqs["min_quality"]]
            print(f"Quality (>= {task_reqs['min_quality']}): {len(domain)} translators left.")
            if domain.empty:
                return

        if "min_on_time_score" in task_reqs:
            domain = domain[domain["ON_TIME_SCORE"] >= task_reqs["min_on_time_score"]]
            print(f"On-Time (>= {task_reqs['min_on_time_score']}): {len(domain)} translators left.")
            if domain.empty:
                return

        if "task_date" in task_reqs:
            task_date = pd.to_datetime(task_reqs["task_date"])
            day_mapping = {"Monday": "MON", "Tuesday": "TUES", "Wednesday": "WED", "Thursday": "THURS", "Friday": "FRI", "Saturday": "SAT", "Sunday": "SUN"}
            schedule_col = day_mapping.get(task_date.day_name())
            if schedule_col in domain.columns:
                domain = domain[domain[schedule_col] == 1]
                print(f"Schedule (Works on {task_date.day_name()}): {len(domain)} translators left.")
                if domain.empty:
                    return

        if "task_length_hours" in task_reqs and "task_start_time" in task_reqs:
            if "START" in domain.columns and "END" in domain.columns:
                clean_start = domain["START"].astype(str).str.replace(".", "", regex=False).str.upper()
                clean_end = domain["END"].astype(str).str.replace(".", "", regex=False).str.upper()
                shift_starts = pd.to_datetime(clean_start, format="mixed", errors="coerce")
                shift_ends = pd.to_datetime(clean_end, format="mixed", errors="coerce")
                shift_ends = shift_ends.mask(shift_ends < shift_starts, shift_ends + pd.Timedelta(days=1))
                task_start = pd.to_datetime(task_reqs["task_start_time"])
                task_end = task_start + pd.Timedelta(hours=task_reqs["task_length_hours"])
                domain = domain[shift_starts <= task_start]
                print(f"Shift Start (<= {task_start.strftime('%H:%M')}): {len(domain)} translators left.")
                if domain.empty:
                    return
                aligned_shift_ends = shift_ends.loc[domain.index]
                domain = domain[aligned_shift_ends >= task_end]
                print(f"Shift End (>= {task_end.strftime('%H:%M')}): {len(domain)} translators left.")
                if domain.empty:
                    return

        for req_name, prefix, label in [
            ("required_subindustry", "SUB", "Sub-Industry"),
            ("required_industry", "IND", "Industry"),
            ("required_industry_group", "GRP", "Industry Group"),
        ]:
            if req_name in task_reqs and task_reqs[req_name]:
                req_list = task_reqs[req_name]
                min_exp = task_reqs.get(f"min_{req_name.replace('required_', '')}_experience", 1.0)
                valid_cols = [f"{prefix}_{x}" for x in req_list if f"{prefix}_{x}" in domain.columns]
                if valid_cols:
                    mask = (domain[valid_cols] >= min_exp).any(axis=1)
                    domain = domain[mask]
                    print(f"{label} Expertise (ANY of {req_list} >= {min_exp} hrs): {len(domain)} translators left.")
                    if domain.empty:
                        print(f"-> BOTTLENECK: Remaining translators lack {label} experience in any of {req_list}.")
                    return
                print(f"FAILED: None of the required {label.lower()} values {req_list} exist in our historical data.")
                return

        print("SUCCESS: Translators are available.")

    def get_eligible_translators(self, task_reqs):
        """
        THE LOGIC CORE: Filters out translators based on requirements and dynamic TASK TYPE business rules.
        Returns a dataframe of all candidates who mathematically pass all tests.
        """
        domain = self.translators_df.copy()
        working_reqs = task_reqs.copy()
        task_type = working_reqs.get("task_type", "Translation")
        followed_by = working_reqs.get("followed_by", None)
        prev_exp = working_reqs.get("previous_translator_experience", 0.0)

        if task_type == "TEST":
            if "max_hourly_rate" in working_reqs:
                del working_reqs["max_hourly_rate"]
        elif task_type == "Training":
            if "min_quality" in working_reqs:
                del working_reqs["min_quality"]
            working_reqs["min_subindustry_experience"] = 0
            working_reqs["min_industry_experience"] = 0
            working_reqs["min_industry_group_experience"] = 0
        elif task_type == "Translation" and followed_by == "ProofReading":
            if "min_quality" in working_reqs:
                working_reqs["min_quality"] = max(0, working_reqs["min_quality"] - 1.0)

        if task_type != "Training":
            task_exp_col = f"{task_type}_experience"
            if task_exp_col in domain.columns:
                domain = domain[domain[task_exp_col] > 0]

        pair = working_reqs.get("language_pair")
        if pair not in domain.columns:
            return pd.DataFrame()
        domain = domain[domain[pair].notna()]

        if "max_hourly_rate" in working_reqs:
            domain = domain[domain[pair] <= working_reqs["max_hourly_rate"]]
        if "min_quality" in working_reqs:
            domain = domain[domain["AVERAGE_QUALITY"] >= working_reqs["min_quality"]]
        if "min_on_time_score" in working_reqs:
            domain = domain[domain["ON_TIME_SCORE"] >= working_reqs["min_on_time_score"]]

        window_days = working_reqs.get("window_days", 1)

        if "task_date" in working_reqs:
            start_date = pd.to_datetime(working_reqs["task_date"])
            day_mapping = {"Monday": "MON", "Tuesday": "TUES", "Wednesday": "WED", "Thursday": "THURS", "Friday": "FRI", "Saturday": "SAT", "Sunday": "SUN"}
            works_any_day = pd.Series(False, index=domain.index)
            for i in range(window_days):
                current_date = start_date + pd.Timedelta(days=i)
                schedule_col = day_mapping.get(current_date.day_name())
                if schedule_col in domain.columns:
                    works_any_day = works_any_day | (domain[schedule_col] == 1)
            domain = domain[works_any_day]

        if "task_length_hours" in working_reqs and "START" in domain.columns and "END" in domain.columns:
            clean_start = domain["START"].astype(str).str.replace(".", "", regex=False).str.upper()
            clean_end = domain["END"].astype(str).str.replace(".", "", regex=False).str.upper()
            shift_starts = pd.to_datetime(clean_start, format="mixed", errors="coerce")
            shift_ends = pd.to_datetime(clean_end, format="mixed", errors="coerce")
            shift_ends = shift_ends.mask(shift_ends < shift_starts, shift_ends + pd.Timedelta(days=1))
            shift_length = (shift_ends - shift_starts).dt.total_seconds() / 3600
            domain["DAILY_CAPACITY"] = shift_length.fillna(0).apply(lambda x: x + 24 if x < 0 else x)
            required_daily_capacity = working_reqs["task_length_hours"] / window_days
            domain = domain[domain["DAILY_CAPACITY"] >= required_daily_capacity]

        def filter_by_list(domain_df, req_list, prefix, min_exp):
            """Helper function to filter dataframe based on a list of acceptable industries."""
            valid_cols = [f"{prefix}_{req}" for req in req_list if f"{prefix}_{req}" in domain_df.columns]
            if not valid_cols:
                return pd.DataFrame()
            if task_type in ["ProofReading", "Spotcheck"] and prev_exp > 0:
                required_exp = max(min_exp, prev_exp + 0.1)
            else:
                required_exp = min_exp
            mask = (domain_df[valid_cols] >= required_exp).any(axis=1)
            return domain_df[mask]

        if "required_subindustry" in working_reqs and working_reqs["required_subindustry"]:
            domain = filter_by_list(domain, working_reqs["required_subindustry"], "SUB", working_reqs.get("min_subindustry_experience", 1.0))
            if domain.empty:
                return domain
        elif "required_industry" in working_reqs and working_reqs["required_industry"]:
            domain = filter_by_list(domain, working_reqs["required_industry"], "IND", working_reqs.get("min_industry_experience", 1.0))
            if domain.empty:
                return domain
        elif "required_industry_group" in working_reqs and working_reqs["required_industry_group"]:
            domain = filter_by_list(domain, working_reqs["required_industry_group"], "GRP", working_reqs.get("min_industry_group_experience", 1.0))
            if domain.empty:
                return domain

        return domain

    def split_task_across_days(self, task_reqs):
        """
        Dynamically splits a task across the exact number of days between the start date and the deadline.
        Ignores strict start hours and focuses purely on Daily Capacity.
        """
        start_date = pd.to_datetime(task_reqs["task_date"])

        if "task_deadline" in task_reqs and pd.notna(task_reqs["task_deadline"]):
            end_date = pd.to_datetime(task_reqs["task_deadline"])
            num_days = max(2, (end_date - start_date).days + 1)
        else:
            num_days = 2
            end_date = start_date + pd.Timedelta(days=1)

        print(f"\n--- INITIATING {num_days}-DAY TASK SPLIT (Deadline: {end_date.strftime('%Y-%m-%d')}) ---")
        domain = self.translators_df.copy()

        pair = task_reqs.get("language_pair")
        if pair in domain.columns:
            domain = domain[domain[pair].notna()]
        if "max_hourly_rate" in task_reqs:
            domain = domain[domain[pair] <= task_reqs["max_hourly_rate"]]
        if "min_quality" in task_reqs:
            domain = domain[domain["AVERAGE_QUALITY"] >= task_reqs["min_quality"]]
        if "min_on_time_score" in task_reqs:
            domain = domain[domain["ON_TIME_SCORE"] >= task_reqs["min_on_time_score"]]

        def filter_by_list(domain_df, req_list, prefix, min_exp):
            valid_cols = [f"{prefix}_{req}" for req in req_list if f"{prefix}_{req}" in domain_df.columns]
            if not valid_cols:
                return pd.DataFrame()
            mask = (domain_df[valid_cols] >= min_exp).any(axis=1)
            return domain_df[mask]

        if "required_subindustry" in task_reqs and task_reqs["required_subindustry"]:
            domain = filter_by_list(domain, task_reqs["required_subindustry"], "SUB", task_reqs.get("min_subindustry_experience", 1.0))
        elif "required_industry" in task_reqs and task_reqs["required_industry"]:
            domain = filter_by_list(domain, task_reqs["required_industry"], "IND", task_reqs.get("min_industry_experience", 1.0))
        elif "required_industry_group" in task_reqs and task_reqs["required_industry_group"]:
            domain = filter_by_list(domain, task_reqs["required_industry_group"], "GRP", task_reqs.get("min_industry_group_experience", 1.0))

        if domain.empty:
            return domain

        day_mapping = {"Monday": "MON", "Tuesday": "TUES", "Wednesday": "WED", "Thursday": "THURS", "Friday": "FRI", "Saturday": "SAT", "Sunday": "SUN"}
        for i in range(num_days):
            current_date = start_date + pd.Timedelta(days=i)
            schedule_col = day_mapping.get(current_date.day_name())
            if schedule_col in domain.columns:
                domain = domain[domain[schedule_col] == 1]

        print(f">> Verified consecutive availability from {start_date.day_name()} to {end_date.day_name()}.")

        if "START" in domain.columns and "END" in domain.columns:
            clean_start = domain["START"].astype(str).str.replace(".", "", regex=False).str.upper()
            clean_end = domain["END"].astype(str).str.replace(".", "", regex=False).str.upper()
            start_times = pd.to_datetime(clean_start, format="mixed", errors="coerce")
            end_times = pd.to_datetime(clean_end, format="mixed", errors="coerce")
            shift_length = (end_times - start_times).dt.total_seconds() / 3600
            domain["DAILY_CAPACITY"] = shift_length.fillna(0).apply(lambda x: x + 24 if x < 0 else x)
            required_daily_capacity = task_reqs.get("task_length_hours", 8) / num_days
            print(f">> Bypassing strict start-time constraints. Task requires {required_daily_capacity:.2f} hours/day of flexible bandwidth.")
            domain = domain[domain["DAILY_CAPACITY"] >= required_daily_capacity]

        if not domain.empty:
            print(f"SUCCESS: Found {len(domain)} translators who have the daily bandwidth to finish this before the deadline.")
        else:
            print("FAILED: No translators have enough flexible daily bandwidth to finish this before the deadline.")

        return domain

    def split_task_across_translators(self, task_reqs, num_translators=2):
        """
        Splits a task so multiple translators can work on it SIMULTANEOUSLY.
        E.g., An 8-hour task needs 2 translators working 4 hours each.
        """
        print(f"\n--- INITIATING PARALLEL SPLIT: {num_translators} TRANSLATORS ---")
        split_reqs = task_reqs.copy()

        if "task_length_hours" in split_reqs:
            split_reqs["task_length_hours"] = split_reqs["task_length_hours"] / num_translators
            if "task_start_time" in split_reqs:
                try:
                    task_start = pd.to_datetime(split_reqs["task_start_time"])
                    task_end = task_start + pd.Timedelta(hours=split_reqs["task_length_hours"])
                    print(f">> Reduced required shift to {split_reqs['task_length_hours']:.2f} hours per translator (between {task_start.strftime('%H:%M')} and {task_end.strftime('%H:%M')}).")
                except Exception:
                    print(f">> Reduced required shift to {split_reqs['task_length_hours']:.2f} hours per translator.")
            else:
                print(f">> Reduced required daily capacity to {split_reqs['task_length_hours']:.2f} hours per translator.")

        domain = self.get_eligible_translators(split_reqs)

        if len(domain) >= num_translators:
            print(f"SUCCESS: Found {len(domain)} available translators. Forming team of {num_translators}.")
            return domain
        print(f"FAILED: Need {num_translators} translators, but only found {len(domain)}.")
        return pd.DataFrame()

    def get_translators_with_fallback(self, task_reqs):
        """
        THE ESCALATION PIPELINE:
        Attempts Strict -> Industry -> Group -> Wildcard -> Global.
        """
        task_effort = task_reqs.get("task_length_hours", 0)
        window_days = task_reqs.get("window_days", 1)
        required_daily = task_effort / window_days

        if required_daily > 10.0:
            print(f"\n[SYSTEM BYPASS] Task requires {required_daily:.2f} hours/day. Bypassing single search and forcing Team Assembly.")
            return pd.DataFrame()

        print("\n--- ATTEMPT 1: Strict Requirements (Sub-Industry Specialist Needed) ---")
        eligible = self.get_eligible_translators(task_reqs)

        if not eligible.empty:
            print(f"SUCCESS: Found {len(eligible)} specialists matching Sub-Industry.")
            return eligible

        print("FAILED: No Sub-Industry specialists found. Initiating Fallback...")
        relaxed_reqs = task_reqs.copy()

        if "required_subindustry" in relaxed_reqs and relaxed_reqs["required_subindustry"] and "required_industry" in relaxed_reqs and relaxed_reqs["required_industry"]:
            print("\n--- ATTEMPT 2: Relaxing to Mid-Level Industry ---")
            del relaxed_reqs["required_subindustry"]
            lvl2_eligible = self.get_eligible_translators(relaxed_reqs)
            if not lvl2_eligible.empty:
                print(f"COMPROMISE SUCCESS: Found {len(lvl2_eligible)} mid-level specialists.")
                return lvl2_eligible
            print("FAILED: Mid-level Industry search didn't yield enough translators.")

        if "required_industry" in relaxed_reqs and relaxed_reqs["required_industry"] and "required_industry_group" in relaxed_reqs and relaxed_reqs["required_industry_group"]:
            print("\n--- ATTEMPT 3: Relaxing to Broad Industry Group ---")
            del relaxed_reqs["required_industry"]
            lvl3_eligible = self.get_eligible_translators(relaxed_reqs)
            if not lvl3_eligible.empty:
                print(f"COMPROMISE SUCCESS: Found {len(lvl3_eligible)} generalists in the Industry Group.")
                return lvl3_eligible
            print("FAILED: Broad Industry Group search failed.")

        wildcard = relaxed_reqs.get("wildcard", "balanced")
        print(f"\n--- ATTEMPT 4: Targeted Wildcard Relaxation ({wildcard.upper()}) ---")

        wildcard_reqs = relaxed_reqs.copy()

        if wildcard == "quality":
            wildcard_reqs["min_quality"] = max(0, wildcard_reqs["min_quality"] - 1.5)
            print(f">> Wildcard Triggered: Lowered minimum quality significantly to {wildcard_reqs['min_quality']}")
        elif wildcard == "price":
            wildcard_reqs["max_hourly_rate"] = wildcard_reqs["max_hourly_rate"] * 1.25
            print(f">> Wildcard Triggered: Increased budget threshold by 25% to ${wildcard_reqs['max_hourly_rate']:.2f}")
        elif wildcard == "deadline" or wildcard == "time":
            wildcard_reqs["min_on_time_score"] = max(0, wildcard_reqs["min_on_time_score"] - 0.20)
            wildcard_reqs["capacity_tolerance"] = 0.70
            print(f">> Wildcard Triggered: Relaxed On-Time score to {wildcard_reqs['min_on_time_score']} and allowed 30% schedule shift")
        else:
            print(">> No specific wildcard provided or recognized. Moving to global relaxation.")

        if wildcard in ["quality", "price", "deadline"]:
            wildcard_eligible = self.get_eligible_translators(wildcard_reqs)
            if not wildcard_eligible.empty:
                print(f"COMPROMISE SUCCESS: Found {len(wildcard_eligible)} translators by flexing the client's {wildcard.upper()} preference.")
                return wildcard_eligible
            print(f"FAILED: Flexing the {wildcard.upper()} was not enough to find a candidate.")

        final_eligible = self.get_eligible_translators(relaxed_reqs)

        if not final_eligible.empty:
            print(f"COMPROMISE SUCCESS: Found {len(final_eligible)} translators using global relaxation.")
            return final_eligible
        print("\nCRITICAL FAILURE: Maximum global relaxation reached. No translators available.")
        return pd.DataFrame()
