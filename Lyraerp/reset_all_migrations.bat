@echo off
echo Deleting all migration files...

REM Delete ERP app migrations
for %%A in (Project Employee UserReq Purchase Tax Items PayTerms HR user customer brand unit chart_of_accounts warehouse stock sales department designation leaves bank allowances journal expenses personaldocuments system_settings email_config sms_config crm sms_templates email_templates activity_log) do (
    if exist "%%A\migrations" (
        del /Q "%%A\migrations\*.py" 2>nul
        echo __init__.py > "%%A\migrations\__init__.py"
        echo Reset %%A migrations
    )
)

REM Delete dual app migrations
for %%A in (company) do (
    if exist "%%A\migrations" (
        del /Q "%%A\migrations\*.py" 2>nul
        echo __init__.py > "%%A\migrations\__init__.py"
        echo Reset %%A migrations
    )
)

echo All migrations deleted!
pause