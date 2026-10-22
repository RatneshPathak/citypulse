"""
CityPulse: Mumbai — Inspection Route Planner

Computes sensible visiting order for top-N priority zones using:
- Nearest-neighbor heuristic for small N
- Haversine distance (straight-line, not road routing)
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
import streamlit as st


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes straight-line distance between two lat/lon points in kilometers.
    
    Uses the haversine formula assuming Earth radius = 6371 km.
    """
    R = 6371.0  # Earth radius in km
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c


def nearest_neighbor_tour(
    locations: pd.DataFrame,
    start_idx: int = 0
) -> Tuple[List[int], float]:
    """
    Computes a greedy nearest-neighbor tour starting from start_idx.
    
    Parameters
    ----------
    locations : pd.DataFrame
        Must have columns: latitude, longitude
    start_idx : int
        Index of starting location
    
    Returns
    -------
    tour : List[int]
        Ordered indices of locations
    total_distance : float
        Total tour distance in km (straight-line)
    """
    n = len(locations)
    unvisited = set(range(n))
    tour = [start_idx]
    unvisited.remove(start_idx)
    total_dist = 0.0
    
    current = start_idx
    while unvisited:
        # Find nearest unvisited location
        nearest = None
        min_dist = float('inf')
        
        for idx in unvisited:
            dist = haversine_distance(
                locations.iloc[current]["latitude"],
                locations.iloc[current]["longitude"],
                locations.iloc[idx]["latitude"],
                locations.iloc[idx]["longitude"],
            )
            if dist < min_dist:
                min_dist = dist
                nearest = idx
        
        tour.append(nearest)
        total_dist += min_dist
        unvisited.remove(nearest)
        current = nearest
    
    return tour, total_dist


@st.cache_data(ttl=3600)
def compute_inspection_route(
    priority_df: pd.DataFrame,
    top_n: int = 5,
    start_station: Optional[str] = None
) -> Tuple[pd.DataFrame, float]:
    """
    Computes an inspection route for the top-N priority zones.
    
    Parameters
    ----------
    priority_df : pd.DataFrame
        Priority rankings with latitude, longitude, station
    top_n : int
        Number of top zones to visit
    start_station : str, optional
        Starting station name. If None, uses highest priority.
    
    Returns
    -------
    route_df : pd.DataFrame
        Ordered route with columns: stop_number, station, latitude, longitude, 
        distance_from_prev (km), cumulative_distance (km)
    total_distance : float
        Total tour distance in km
    """
    # Filter to top-N
    top_locs = priority_df.head(top_n).copy()
    
    # Determine start index
    if start_station and start_station in top_locs["station"].values:
        start_idx = top_locs[top_locs["station"] == start_station].index[0]
        start_idx = list(top_locs.index).index(start_idx)
    else:
        start_idx = 0
    
    # Compute tour
    tour_indices, total_dist = nearest_neighbor_tour(
        top_locs[["latitude", "longitude"]].reset_index(drop=True),
        start_idx=start_idx
    )
    
    # Build route dataframe
    route_data = []
    cumulative = 0.0
    
    for i, idx in enumerate(tour_indices):
        row = top_locs.iloc[idx]
        
        if i == 0:
            dist_from_prev = 0.0
        else:
            prev_row = top_locs.iloc[tour_indices[i-1]]
            dist_from_prev = haversine_distance(
                prev_row["latitude"], prev_row["longitude"],
                row["latitude"], row["longitude"]
            )
        
        cumulative += dist_from_prev
        
        route_data.append({
            "stop_number": i + 1,
            "station": row["station"],
            "zone": row.get("zone", "MMR"),
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "priority_score": row.get("priority_score", 0),
            "latest_aqi": row.get("latest_aqi", 0),
            "distance_from_prev_km": round(dist_from_prev, 2),
            "cumulative_distance_km": round(cumulative, 2),
        })
    
    return pd.DataFrame(route_data), round(total_dist, 2)
