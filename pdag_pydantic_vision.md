# PDAG with Pydantic Models as Parameter Types

This document outlines how `pdag` could support Pydantic models as parameter types, allowing users to define rich, structured data types for their parameters while maintaining the simplicity and flexibility of the existing API.

## Core Concept

Instead of being limited to basic types like `float`, `str`, `bool`, users can define complex structured data using Pydantic models and use them directly as parameter types in pdag models.

## Basic Example: Location as a Pydantic Model

### Current Approach (Categorical Parameter)

```python
import pdag

class DiamondMdpModel(pdag.Model):
    location = pdag.CategoricalParameter(
        "location",
        categories=("start", "left", "right", "end"),
        is_time_series=True
    )
```

### With Pydantic Model Support

```python
from pydantic import BaseModel, Field
from typing import Literal
import pdag

class Location(BaseModel):
    """Rich location model with additional metadata."""
    position: Literal["start", "left", "right", "end"]
    coordinates: tuple[float, float] = Field(default=(0.0, 0.0))
    visited_count: int = Field(default=0, ge=0)

    def is_terminal(self) -> bool:
        return self.position == "end"

class DiamondMdpModel(pdag.Model):
    # Use the Pydantic model directly as a parameter type
    location = pdag.PydanticParameter("location", Location, is_time_series=True)

    @pdag.relationship(at_each_time_step=True)
    def state_transition(
        self,
        location: Annotated[Location, location.ref()],
        action: Annotated[str, action.ref()]
    ) -> Annotated[Location, location.ref(next=True)]:
        """Transition to next location with rich state tracking."""

        # Work with the rich Location object
        if location.position == "start" and action == "go_left":
            return Location(
                position="left",
                coordinates=(-1.0, 0.0),
                visited_count=location.visited_count + 1
            )
        # ... other transitions
```

## Complex Structured Data

### Game State Example

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import pdag

class Player(BaseModel):
    """Player state in a game."""
    health: int = Field(ge=0, le=100)
    position: tuple[float, float]
    inventory: Dict[str, int] = Field(default_factory=dict)
    level: int = Field(default=1, ge=1)

class GameState(BaseModel):
    """Complete game state."""
    players: Dict[str, Player]
    turn: int = Field(default=0, ge=0)
    board_state: List[List[str]] = Field(default_factory=list)
    game_over: bool = Field(default=False)

    def get_active_player(self) -> Player:
        player_ids = list(self.players.keys())
        return self.players[player_ids[self.turn % len(player_ids)]]

class GameModel(pdag.Model):
    """Game simulation model."""

    # Rich structured parameter
    state = pdag.PydanticParameter("state", GameState, is_time_series=True)

    @pdag.relationship(at_each_time_step=True)
    def process_turn(
        self,
        state: Annotated[GameState, state.ref()],
        action: Annotated[str, action.ref()]
    ) -> Annotated[GameState, state.ref(next=True)]:
        """Process a game turn with rich state manipulation."""

        # Work directly with the structured data
        active_player = state.get_active_player()

        # Modify the game state
        new_state = state.model_copy(deep=True)
        new_state.turn += 1

        # Update player based on action
        if action == "move_up":
            x, y = active_player.position
            new_state.players[list(new_state.players.keys())[0]].position = (x, y + 1)

        return new_state
```

## Scientific/Engineering Applications

### Physical System State

```python
from pydantic import BaseModel, Field
from typing import Optional
import pdag

class MaterialProperties(BaseModel):
    """Properties of a material."""
    density: float = Field(gt=0, description="Density in kg/m³")
    thermal_conductivity: float = Field(gt=0, description="Thermal conductivity in W/m·K")
    specific_heat: float = Field(gt=0, description="Specific heat in J/kg·K")

    def thermal_diffusivity(self) -> float:
        return self.thermal_conductivity / (self.density * self.specific_heat)

class ThermalState(BaseModel):
    """Thermal state of a system."""
    temperature: float = Field(description="Temperature in Kelvin", gt=0)
    heat_flux: float = Field(description="Heat flux in W/m²")
    material: MaterialProperties

    def validate_state(self) -> bool:
        """Validate physical constraints."""
        return self.temperature < 1000  # Melting point check

class ThermalModel(pdag.Model):
    """Heat transfer simulation model."""

    # Rich thermal state parameter
    thermal_state = pdag.PydanticParameter("thermal_state", ThermalState, is_time_series=True)

    @pdag.relationship(at_each_time_step=True)
    def heat_transfer(
        self,
        thermal_state: Annotated[ThermalState, thermal_state.ref()],
        boundary_temp: Annotated[float, boundary_temp.ref()]
    ) -> Annotated[ThermalState, thermal_state.ref(next=True)]:
        """Calculate heat transfer using rich material properties."""

        # Use the rich methods and properties
        diffusivity = thermal_state.material.thermal_diffusivity()

        # Calculate temperature change
        temp_diff = boundary_temp - thermal_state.temperature
        new_temp = thermal_state.temperature + 0.1 * diffusivity * temp_diff

        return thermal_state.model_copy(update={
            "temperature": new_temp,
            "heat_flux": diffusivity * temp_diff
        })
```

## Nested and Hierarchical Models

### Robotics Example

```python
from pydantic import BaseModel, Field
from typing import List
import pdag

class Joint(BaseModel):
    """Robot joint state."""
    angle: float = Field(description="Joint angle in radians")
    velocity: float = Field(default=0.0, description="Angular velocity")
    torque: float = Field(default=0.0, description="Applied torque")

    def is_at_limit(self, min_angle: float, max_angle: float) -> bool:
        return self.angle <= min_angle or self.angle >= max_angle

class RobotArm(BaseModel):
    """Robot arm configuration."""
    joints: List[Joint] = Field(description="List of joint states")
    end_effector_position: tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0))

    def forward_kinematics(self) -> tuple[float, float, float]:
        """Calculate end effector position from joint angles."""
        # Simplified forward kinematics
        x = sum(joint.angle * 0.1 for joint in self.joints)
        y = sum(joint.angle * 0.05 for joint in self.joints)
        z = 0.0
        return (x, y, z)

class RobotModel(pdag.Model):
    """Robot control model."""

    # Complex hierarchical parameter
    arm_state = pdag.PydanticParameter("arm_state", RobotArm, is_time_series=True)

    @pdag.relationship(at_each_time_step=True)
    def control_step(
        self,
        arm_state: Annotated[RobotArm, arm_state.ref()],
        target_position: Annotated[tuple[float, float, float], target_position.ref()]
    ) -> Annotated[RobotArm, arm_state.ref(next=True)]:
        """Control robot arm to reach target position."""

        # Use rich model methods
        current_position = arm_state.forward_kinematics()

        # Simple control logic
        new_joints = []
        for joint in arm_state.joints:
            # Adjust joint angles toward target
            new_angle = joint.angle + 0.01  # Simple increment
            new_joints.append(joint.model_copy(update={"angle": new_angle}))

        # Update arm state
        new_arm = arm_state.model_copy(update={"joints": new_joints})
        new_arm.end_effector_position = new_arm.forward_kinematics()

        return new_arm
```

## Validation and Constraints

### Financial Model with Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Dict, Optional
from decimal import Decimal
import pdag

class Portfolio(BaseModel):
    """Investment portfolio state."""
    holdings: Dict[str, Decimal] = Field(description="Asset holdings")
    cash: Decimal = Field(ge=0, description="Available cash")
    total_value: Optional[Decimal] = Field(description="Total portfolio value")

    @validator('holdings')
    def validate_holdings(cls, v):
        if any(amount < 0 for amount in v.values()):
            raise ValueError("Holdings cannot be negative")
        return v

    def calculate_total_value(self, prices: Dict[str, Decimal]) -> Decimal:
        """Calculate total portfolio value."""
        return sum(amount * prices.get(asset, Decimal('0'))
                  for asset, amount in self.holdings.items()) + self.cash

class TradingModel(pdag.Model):
    """Trading strategy model."""

    # Financial state with built-in validation
    portfolio = pdag.PydanticParameter("portfolio", Portfolio, is_time_series=True)

    @pdag.relationship(at_each_time_step=True)
    def execute_trade(
        self,
        portfolio: Annotated[Portfolio, portfolio.ref()],
        market_prices: Annotated[Dict[str, Decimal], market_prices.ref()],
        trade_signal: Annotated[str, trade_signal.ref()]
    ) -> Annotated[Portfolio, portfolio.ref(next=True)]:
        """Execute trading strategy with automatic validation."""

        # Pydantic automatically validates the portfolio structure
        total_value = portfolio.calculate_total_value(market_prices)

        # Execute trade logic
        new_portfolio = portfolio.model_copy(deep=True)

        if trade_signal == "buy_stock":
            # Buy logic with validation
            new_portfolio.holdings["AAPL"] = portfolio.holdings.get("AAPL", Decimal('0')) + Decimal('10')
            new_portfolio.cash -= Decimal('1000')

        # Pydantic will validate the new portfolio state
        return new_portfolio
```

## Key Benefits

### 1. **Rich Data Modeling**

- Define complex, structured data types with methods and properties
- Automatic validation and serialization
- Type safety with IDE support

### 2. **Domain-Specific Types**

- Create domain-specific parameter types (Location, Player, ThermalState)
- Encapsulate domain logic within the parameter type
- Reusable across different models

### 3. **Validation and Constraints**

- Automatic validation of parameter values
- Custom validators for domain-specific rules
- Clear error messages for invalid states

### 4. **Seamless Integration**

- Works with existing pdag features (time-series, relationships, references)
- No change to the core pdag API
- Backward compatible with existing parameter types

### 5. **Serialization Support**

- Easy JSON/dict conversion for configuration and persistence
- Integration with databases and APIs
- Configuration management for complex parameter sets

## API Design

```python
# New parameter type for Pydantic models
class PydanticParameter(pdag.Parameter):
    def __init__(self, name: str, model_class: Type[BaseModel], **kwargs):
        self.model_class = model_class
        super().__init__(name, **kwargs)
```

This approach makes pdag much more flexible by allowing users to define rich, structured parameter types while keeping the existing API simple and familiar.
