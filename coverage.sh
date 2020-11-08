#!/bin/bash
coverage combine .coverage-*
coverage html --fail-under 100
