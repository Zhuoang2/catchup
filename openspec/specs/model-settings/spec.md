# model-settings Specification

## Purpose
Lets the instance owner connect CatchUp to an OpenAI-compatible model provider of their choice, verify the connection, and choose a model, while keeping the API key protected.

## Requirements

### Requirement: Configure an OpenAI-compatible provider
The system SHALL let the user save a provider configuration consisting of a base URL, an API key, and a model ID. Only one configuration is active at a time.

#### Scenario: Save a configuration
- **WHEN** the user submits a base URL, an API key, and a model ID
- **THEN** the system stores the configuration and later reads report the base URL, the model ID, and that a key is set

#### Scenario: Update without re-entering the key
- **WHEN** the user changes the model ID and leaves the key field empty
- **THEN** the system keeps the previously stored key

### Requirement: Test the connection and list models
The system SHALL let the user test a configuration before or after saving it. A successful test MUST return the provider's available model IDs so the user can pick one. The system MUST NOT rely on a hard-coded model list.

#### Scenario: Valid credentials
- **WHEN** the user tests a configuration with a valid base URL and key
- **THEN** the system reports success and returns the provider's model IDs

#### Scenario: Invalid key
- **WHEN** the provider rejects the key
- **THEN** the system reports that the API key was rejected, without exposing the key

#### Scenario: Unreachable provider
- **WHEN** the base URL cannot be reached or does not answer within 15 seconds
- **THEN** the system reports a connection error that names the base URL

### Requirement: Protect the stored API key
The system MUST store the API key encrypted, using a secret supplied through the instance's environment. The system MUST NOT return the key through any API response or write it to logs. It MAY return only the key's last four characters.

#### Scenario: Reading settings
- **WHEN** any client reads the model settings
- **THEN** the response contains no full API key, only whether a key is set and its last four characters

#### Scenario: Missing instance secret
- **WHEN** the user tries to save an API key and the instance secret is not configured
- **THEN** the system refuses to save and explains how to set the secret

### Requirement: Never send the stored key to a different provider address
The system MUST use the stored API key only with the stored base URL. A save or connection test that changes the base URL MUST include a new API key.

#### Scenario: Base URL changed without a key
- **WHEN** a key is stored for one base URL and the user saves or tests a different base URL without entering a key
- **THEN** the request is refused with a message asking for the API key, and no request is sent to the new address

### Requirement: Accept requests only for allowed hosts
The system MUST reject HTTP requests whose Host header is not in the instance's configured list of allowed hosts. By default, the list contains only local addresses.

#### Scenario: Request for an unknown host
- **WHEN** a request arrives with a Host header that is not in the allowed list
- **THEN** the system rejects it without performing the requested action

### Requirement: Report provider errors meaningfully
When a model call fails, the system SHALL distinguish authentication failure, insufficient balance, rate limiting, and temporary provider errors, and show the user a message suited to each.

#### Scenario: Insufficient balance
- **WHEN** the provider responds that the account balance is insufficient
- **THEN** the user sees a message saying the provider account has insufficient balance
