#!/bin/bash
nginx &
exec streamlit run app_paid.py --server.port=8501 --server.address=127.0.0.1
