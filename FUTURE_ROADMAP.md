# CityPulse: future roadmap (not implemented)

These are ideas only. None are part of the hackathon submission.

- **Authentication:** optional sign-in for municipal staff using an established library or the host's
  identity provider. No passwords stored by CityPulse itself.
- **Admin roles:** viewer (read dashboards), analyst (rerun the pipeline), admin (edit action library and
  responsible roles).
- **SQLite metadata:** store run history (run time, data range, file hashes, metrics) and an audit log of
  which actions were reviewed. Keep raw measurements in CSV/Parquet.
- **Subscription tiers:** possible free tier (public four-station view) and a paid tier (more stations,
  alerts by email), only after data licences allow redistribution.
- **Data and model:** more stations, weather inputs, scheduled refresh, and re-testing machine learning
  against the persistence baseline.
