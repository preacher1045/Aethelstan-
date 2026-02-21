from typing import Any, Dict, List, Optional
from psycopg2 import sql
from backend.storage.db_conn import db_connection


def _fetch_one(query: sql.SQL, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
	with db_connection() as conn:
		with conn.cursor() as cur:
			cur.execute(query, params or {})
			return cur.fetchone()


def _fetch_all(query: sql.SQL, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
	with db_connection() as conn:
		with conn.cursor() as cur:
			cur.execute(query, params or {})
			return cur.fetchall()


def _insert_row(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
	if not data:
		raise ValueError("Insert data must not be empty.")

	columns = [sql.Identifier(key) for key in data.keys()]
	placeholders = [sql.Placeholder(key) for key in data.keys()]
	query = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({vals}) RETURNING *").format(
		table=sql.Identifier(table),
		cols=sql.SQL(", ").join(columns),
		vals=sql.SQL(", ").join(placeholders),
	)
	return _fetch_one(query, data) or {}


def _update_row(
	table: str,
	key_column: str,
	key_value: Any,
	data: Dict[str, Any],
	touch_updated_at: bool = False,
) -> Optional[Dict[str, Any]]:
	if not data and not touch_updated_at:
		return None

	set_clauses = []
	params: Dict[str, Any] = {}
	for idx, (column, value) in enumerate(data.items()):
		param_key = f"val_{idx}"
		set_clauses.append(
			sql.SQL("{col} = {val}").format(
				col=sql.Identifier(column),
				val=sql.Placeholder(param_key),
			)
		)
		params[param_key] = value

	if touch_updated_at and "updated_at" not in data:
		set_clauses.append(sql.SQL("updated_at = CURRENT_TIMESTAMP"))

	if not set_clauses:
		return None

	params["key_value"] = key_value
	query = sql.SQL("UPDATE {table} SET {sets} WHERE {key} = {key_val} RETURNING *").format(
		table=sql.Identifier(table),
		sets=sql.SQL(", ").join(set_clauses),
		key=sql.Identifier(key_column),
		key_val=sql.Placeholder("key_value"),
	)
	return _fetch_one(query, params)


def _delete_row(table: str, key_column: str, key_value: Any) -> Optional[Dict[str, Any]]:
	query = sql.SQL("DELETE FROM {table} WHERE {key} = {key_val} RETURNING *").format(
		table=sql.Identifier(table),
		key=sql.Identifier(key_column),
		key_val=sql.Placeholder("key_value"),
	)
	return _fetch_one(query, {"key_value": key_value})


# -------------------------------------------------------------------
# PCAP Sessions
# -------------------------------------------------------------------
def create_pcap_session(data: Dict[str, Any]) -> Dict[str, Any]:
	return _insert_row("pcap_sessions", data)


def get_pcap_session(session_id: str) -> Optional[Dict[str, Any]]:
	query = sql.SQL("SELECT * FROM pcap_sessions WHERE session_id = {val}").format(
		val=sql.Placeholder("session_id")
	)
	return _fetch_one(query, {"session_id": session_id})


def list_pcap_sessions(
	status: Optional[str] = None, limit: int = 100, offset: int = 0
) -> List[Dict[str, Any]]:
	params: Dict[str, Any] = {"limit": limit, "offset": offset}
	where_clause = sql.SQL("")
	if status:
		where_clause = sql.SQL("WHERE status = {status}").format(
			status=sql.Placeholder("status")
		)
		params["status"] = status

	query = sql.SQL(
		"SELECT * FROM pcap_sessions {where} ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
	).format(where=where_clause, limit=sql.Placeholder("limit"), offset=sql.Placeholder("offset"))
	return _fetch_all(query, params)


def update_pcap_session(session_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
	return _update_row(
		"pcap_sessions",
		"session_id",
		session_id,
		data,
		touch_updated_at=True,
	)


def delete_pcap_session(session_id: str) -> Optional[Dict[str, Any]]:
	return _delete_row("pcap_sessions", "session_id", session_id)


# -------------------------------------------------------------------
# Traffic Windows
# -------------------------------------------------------------------
def create_traffic_window(data: Dict[str, Any]) -> Dict[str, Any]:
	return _insert_row("traffic_windows", data)


def get_traffic_window(window_id: int) -> Optional[Dict[str, Any]]:
	query = sql.SQL("SELECT * FROM traffic_windows WHERE id = {val}").format(
		val=sql.Placeholder("window_id")
	)
	return _fetch_one(query, {"window_id": window_id})


def get_traffic_window_by_session(session_id: str, window_id: int) -> Optional[Dict[str, Any]]:
	query = sql.SQL(
		"SELECT * FROM traffic_windows WHERE session_id = {session_id} AND window_id = {window_id}"
	).format(
		session_id=sql.Placeholder("session_id"),
		window_id=sql.Placeholder("window_id"),
	)
	return _fetch_one(query, {"session_id": session_id, "window_id": window_id})


def list_traffic_windows(
	session_id: Optional[str] = None, limit: int = 100, offset: int = 0
) -> List[Dict[str, Any]]:
	params: Dict[str, Any] = {"limit": limit, "offset": offset}
	where_clause = sql.SQL("")
	if session_id:
		where_clause = sql.SQL("WHERE session_id = {session_id}").format(
			session_id=sql.Placeholder("session_id")
		)
		params["session_id"] = session_id

	query = sql.SQL(
		"SELECT * FROM traffic_windows {where} ORDER BY window_start ASC LIMIT {limit} OFFSET {offset}"
	).format(where=where_clause, limit=sql.Placeholder("limit"), offset=sql.Placeholder("offset"))
	return _fetch_all(query, params)


def update_traffic_window(window_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
	return _update_row("traffic_windows", "id", window_id, data)


def delete_traffic_window(window_id: int) -> Optional[Dict[str, Any]]:
	return _delete_row("traffic_windows", "id", window_id)


# -------------------------------------------------------------------
# Flows (Top Flows)
# -------------------------------------------------------------------
def create_flow(data: Dict[str, Any]) -> Dict[str, Any]:
	return _insert_row("flows", data)


def list_flows(
	session_id: Optional[str] = None, limit: int = 100, offset: int = 0
) -> List[Dict[str, Any]]:
	params: Dict[str, Any] = {"limit": limit, "offset": offset}
	where_clause = sql.SQL("")
	if session_id:
		where_clause = sql.SQL("WHERE session_id = {session_id}").format(
			session_id=sql.Placeholder("session_id")
		)
		params["session_id"] = session_id

	query = sql.SQL(
		"SELECT * FROM flows {where} ORDER BY total_bytes DESC LIMIT {limit} OFFSET {offset}"
	).format(where=where_clause, limit=sql.Placeholder("limit"), offset=sql.Placeholder("offset"))
	return _fetch_all(query, params)


# -------------------------------------------------------------------
# Port Stats (Port Usage Distribution)
# -------------------------------------------------------------------
def create_port_stat(data: Dict[str, Any]) -> Dict[str, Any]:
	return _insert_row("port_stats", data)


def list_port_stats(
	session_id: Optional[str] = None, limit: int = 100, offset: int = 0
) -> List[Dict[str, Any]]:
	params: Dict[str, Any] = {"limit": limit, "offset": offset}
	where_clause = sql.SQL("")
	if session_id:
		where_clause = sql.SQL("WHERE session_id = {session_id}").format(
			session_id=sql.Placeholder("session_id")
		)
		params["session_id"] = session_id

	query = sql.SQL(
		"SELECT * FROM port_stats {where} ORDER BY total_bytes DESC LIMIT {limit} OFFSET {offset}"
	).format(where=where_clause, limit=sql.Placeholder("limit"), offset=sql.Placeholder("offset"))
	return _fetch_all(query, params)


# -------------------------------------------------------------------
# Anomaly Results
# -------------------------------------------------------------------
def create_anomaly_result(data: Dict[str, Any]) -> Dict[str, Any]:
	return _insert_row("anomaly_results", data)


def get_anomaly_result(result_id: int) -> Optional[Dict[str, Any]]:
	query = sql.SQL("SELECT * FROM anomaly_results WHERE id = {val}").format(
		val=sql.Placeholder("result_id")
	)
	return _fetch_one(query, {"result_id": result_id})


def list_anomaly_results(
	session_id: Optional[str] = None,
	is_anomaly: Optional[bool] = None,
	limit: int = 100,
	offset: int = 0,
) -> List[Dict[str, Any]]:
	params: Dict[str, Any] = {"limit": limit, "offset": offset}
	where_parts = []

	if session_id:
		where_parts.append(sql.SQL("session_id = {session_id}").format(
			session_id=sql.Placeholder("session_id")
		))
		params["session_id"] = session_id

	if is_anomaly is not None:
		where_parts.append(sql.SQL("is_anomaly = {is_anomaly}").format(
			is_anomaly=sql.Placeholder("is_anomaly")
		))
		params["is_anomaly"] = is_anomaly

	where_clause = sql.SQL("")
	if where_parts:
		where_clause = sql.SQL("WHERE ") + sql.SQL(" AND ").join(where_parts)

	query = sql.SQL(
		"SELECT * FROM anomaly_results {where} ORDER BY detected_at DESC LIMIT {limit} OFFSET {offset}"
	).format(where=where_clause, limit=sql.Placeholder("limit"), offset=sql.Placeholder("offset"))
	return _fetch_all(query, params)


def update_anomaly_result(result_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
	return _update_row("anomaly_results", "id", result_id, data)


def delete_anomaly_result(result_id: int) -> Optional[Dict[str, Any]]:
	return _delete_row("anomaly_results", "id", result_id)


# -------------------------------------------------------------------
# Insights
# -------------------------------------------------------------------
def create_insight(data: Dict[str, Any]) -> Dict[str, Any]:
	return _insert_row("insights", data)


def get_insight(insight_id: int) -> Optional[Dict[str, Any]]:
	query = sql.SQL("SELECT * FROM insights WHERE id = {val}").format(
		val=sql.Placeholder("insight_id")
	)
	return _fetch_one(query, {"insight_id": insight_id})


def list_insights(
	session_id: Optional[str] = None,
	status: Optional[str] = None,
	limit: int = 100,
	offset: int = 0,
) -> List[Dict[str, Any]]:
	params: Dict[str, Any] = {"limit": limit, "offset": offset}
	where_parts = []

	if session_id:
		where_parts.append(sql.SQL("session_id = {session_id}").format(
			session_id=sql.Placeholder("session_id")
		))
		params["session_id"] = session_id

	if status:
		where_parts.append(sql.SQL("status = {status}").format(
			status=sql.Placeholder("status")
		))
		params["status"] = status

	where_clause = sql.SQL("")
	if where_parts:
		where_clause = sql.SQL("WHERE ") + sql.SQL(" AND ").join(where_parts)

	query = sql.SQL(
		"SELECT * FROM insights {where} ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
	).format(where=where_clause, limit=sql.Placeholder("limit"), offset=sql.Placeholder("offset"))
	return _fetch_all(query, params)


def update_insight(insight_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
	return _update_row("insights", "id", insight_id, data, touch_updated_at=True)


def delete_insight(insight_id: int) -> Optional[Dict[str, Any]]:
	return _delete_row("insights", "id", insight_id)
