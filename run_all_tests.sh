#!/bin/bash
# Script to run all tests

echo "Running Python tests with pytest..."
pytest

echo "Running Python tests with unittest..."
python -m unittest discover -s test -p 'test_*.py'

echo "Running Go tests..."
go test ./golang/...