"""CRUD operations for database models."""

import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Frame, Session, Signal, DeviceProfile, DeviceSetup


class SessionCRUD:
    """CRUD operations for Session model."""

    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        car_id: Optional[str] = None,
        driver: Optional[str] = None,
        track: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Session:
        """Create a new session.

        Args:
            db: Database session.
            name: Session name.
            car_id: Optional car ID.
            driver: Optional driver name.
            track: Optional track name.
            notes: Optional session notes.

        Returns:
            Created session.
        """
        session = Session(
            name=name,
            car_id=car_id,
            driver=driver,
            track=track,
            notes=notes,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_by_id(db: AsyncSession, session_id: int) -> Optional[Session]:
        """Get session by ID.

        Args:
            db: Database session.
            session_id: Session ID.

        Returns:
            Session if found, None otherwise.
        """
        result = await db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(db: AsyncSession, limit: int = 100, offset: int = 0) -> List[Session]:
        """Get all sessions.

        Args:
            db: Database session.
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip.

        Returns:
            List of sessions.
        """
        result = await db.execute(
            select(Session)
            .order_by(Session.created_utc.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession,
        session_id: int,
        **kwargs,
    ) -> Optional[Session]:
        """Update session.

        Args:
            db: Database session.
            session_id: Session ID.
            **kwargs: Fields to update.

        Returns:
            Updated session if found, None otherwise.
        """
        session = await SessionCRUD.get_by_id(db, session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            await db.commit()
            await db.refresh(session)
        return session

    @staticmethod
    async def delete(db: AsyncSession, session_id: int) -> bool:
        """Delete session.

        Args:
            db: Database session.
            session_id: Session ID.

        Returns:
            True if deleted, False if not found.
        """
        session = await SessionCRUD.get_by_id(db, session_id)
        if session:
            await db.delete(session)
            await db.commit()
            return True
        return False


class SignalCRUD:
    """CRUD operations for Signal model."""

    @staticmethod
    async def create(
        db: AsyncSession,
        session_id: int,
        source: str,
        channel: str,
        ts_utc: Optional[datetime] = None,
        ts_mono_ns: Optional[int] = None,
        value_num: Optional[float] = None,
        value_text: Optional[str] = None,
        unit: Optional[str] = None,
        quality: str = "good",
    ) -> Signal:
        """Create a new signal.

        Args:
            db: Database session.
            session_id: Session ID.
            source: Signal source.
            channel: Signal channel.
            ts_utc: UTC timestamp.
            ts_mono_ns: Monotonic timestamp in nanoseconds.
            value_num: Numeric value.
            value_text: Text value.
            unit: Unit of measurement.
            quality: Signal quality.

        Returns:
            Created signal.
        """
        if ts_utc is None:
            ts_utc = datetime.now(timezone.utc)
        if ts_mono_ns is None:
            import time
            ts_mono_ns = int(time.monotonic_ns())

        signal = Signal(
            session_id=session_id,
            source=source,
            channel=channel,
            ts_utc=ts_utc,
            ts_mono_ns=ts_mono_ns,
            value_num=value_num,
            value_text=value_text,
            unit=unit,
            quality=quality,
        )
        db.add(signal)
        await db.commit()
        await db.refresh(signal)
        return signal

    @staticmethod
    async def create_batch(db: AsyncSession, signals_data: List[dict]) -> List[Signal]:
        """Create multiple signals in batch.

        Args:
            db: Database session.
            signals_data: List of signal data dictionaries.

        Returns:
            List of created signals.
        """
        signals = []
        for data in signals_data:
            signal = Signal(**data)
            signals.append(signal)
            db.add(signal)
        
        await db.commit()
        for signal in signals:
            await db.refresh(signal)
        return signals

    @staticmethod
    async def get_by_session(
        db: AsyncSession,
        session_id: int,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Signal]:
        """Get signals by session ID.

        Args:
            db: Database session.
            session_id: Session ID.
            limit: Maximum number of signals to return.
            offset: Number of signals to skip.

        Returns:
            List of signals.
        """
        result = await db.execute(
            select(Signal)
            .where(Signal.session_id == session_id)
            .order_by(Signal.ts_utc.asc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def get_signals_paginated(
        db: AsyncSession,
        session_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sources: Optional[List[str]] = None,
        channels: Optional[List[str]] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Signal]:
        """Get signals with pagination and filtering.

        Args:
            db: Database session.
            session_id: Session ID to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.
            sources: Optional list of sources to filter by.
            channels: Optional list of channels to filter by.
            limit: Maximum number of signals to return.
            offset: Number of signals to skip.

        Returns:
            List of signals matching the criteria.
        """
        query = select(Signal).where(Signal.session_id == session_id)
        
        # Add time filters
        if start_time:
            query = query.where(Signal.ts_utc >= start_time)
        if end_time:
            query = query.where(Signal.ts_utc <= end_time)
        
        # Add source filters
        if sources:
            query = query.where(Signal.source.in_(sources))
        
        # Add channel filters
        if channels:
            query = query.where(Signal.channel.in_(channels))
        
        # Add ordering and pagination
        query = query.order_by(Signal.ts_utc.asc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()


class FrameCRUD:
    """CRUD operations for Frame model."""

    @staticmethod
    async def create(
        db: AsyncSession,
        session_id: int,
        payload_json: str,
        ts_utc: Optional[datetime] = None,
        ts_mono_ns: Optional[int] = None,
    ) -> Frame:
        """Create a new frame.

        Args:
            db: Database session.
            session_id: Session ID.
            payload_json: JSON payload.
            ts_utc: UTC timestamp.
            ts_mono_ns: Monotonic timestamp in nanoseconds.

        Returns:
            Created frame.
        """
        if ts_utc is None:
            ts_utc = datetime.now(timezone.utc)
        if ts_mono_ns is None:
            import time
            ts_mono_ns = int(time.monotonic_ns())

        frame = Frame(
            session_id=session_id,
            ts_utc=ts_utc,
            ts_mono_ns=ts_mono_ns,
            payload_json=payload_json,
        )
        db.add(frame)
        await db.commit()
        await db.refresh(frame)
        return frame

    @staticmethod
    async def create_batch(db: AsyncSession, frames_data: List[dict]) -> List[Frame]:
        """Create multiple frames in batch.

        Args:
            db: Database session.
            frames_data: List of frame data dictionaries.

        Returns:
            List of created frames.
        """
        frames = []
        for data in frames_data:
            frame = Frame(**data)
            frames.append(frame)
            db.add(frame)
        
        await db.commit()
        for frame in frames:
            await db.refresh(frame)
        return frames

    @staticmethod
    async def get_by_session(
        db: AsyncSession,
        session_id: int,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Frame]:
        """Get frames by session ID.

        Args:
            db: Database session.
            session_id: Session ID.
            limit: Maximum number of frames to return.
            offset: Number of frames to skip.

        Returns:
            List of frames.
        """
        result = await db.execute(
            select(Frame)
            .where(Frame.session_id == session_id)
            .order_by(Frame.ts_utc.asc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def get_frames_paginated(
        db: AsyncSession,
        session_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Frame]:
        """Get frames with pagination and filtering.

        Args:
            db: Database session.
            session_id: Session ID to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.
            limit: Maximum number of frames to return.
            offset: Number of frames to skip.

        Returns:
            List of frames matching the criteria.
        """
        query = select(Frame).where(Frame.session_id == session_id)
        
        # Add time filters
        if start_time:
            query = query.where(Frame.ts_utc >= start_time)
        if end_time:
            query = query.where(Frame.ts_utc <= end_time)
        
        # Add ordering and pagination
        query = query.order_by(Frame.ts_utc.asc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()


class DeviceProfileCRUD:
    """CRUD operations for DeviceProfile model."""

    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        description: Optional[str] = None,
        gps_config: Optional[dict] = None,
        obd_config: Optional[dict] = None,
        meshtastic_config: Optional[dict] = None,
        custom_config: Optional[dict] = None,
        is_default: bool = False,
    ) -> DeviceProfile:
        """Create a new device profile.

        Args:
            db: Database session.
            name: Profile name.
            description: Optional description.
            gps_config: GPS configuration.
            obd_config: OBD configuration.
            meshtastic_config: Meshtastic configuration.
            custom_config: Custom configuration.
            is_default: Whether this is the default profile.

        Returns:
            Created device profile.
        """
        # If this is set as default, unset other defaults
        if is_default:
            await DeviceProfileCRUD.unset_default(db)

        profile = DeviceProfile(
            name=name,
            description=description,
            gps_config=json.dumps(gps_config) if gps_config else None,
            obd_config=json.dumps(obd_config) if obd_config else None,
            meshtastic_config=json.dumps(meshtastic_config) if meshtastic_config else None,
            custom_config=json.dumps(custom_config) if custom_config else None,
            is_default=is_default,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def get_by_id(db: AsyncSession, profile_id: int) -> Optional[DeviceProfile]:
        """Get device profile by ID.

        Args:
            db: Database session.
            profile_id: Profile ID.

        Returns:
            Device profile if found, None otherwise.
        """
        result = await db.execute(select(DeviceProfile).where(DeviceProfile.id == profile_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(db: AsyncSession, limit: int = 100, offset: int = 0) -> List[DeviceProfile]:
        """Get all device profiles.

        Args:
            db: Database session.
            limit: Maximum number of profiles to return.
            offset: Number of profiles to skip.

        Returns:
            List of device profiles.
        """
        result = await db.execute(
            select(DeviceProfile)
            .order_by(DeviceProfile.is_default.desc(), DeviceProfile.created_utc.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def get_default(db: AsyncSession) -> Optional[DeviceProfile]:
        """Get the default device profile.

        Args:
            db: Database session.

        Returns:
            Default device profile if found, None otherwise.
        """
        result = await db.execute(select(DeviceProfile).where(DeviceProfile.is_default == True))
        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        profile_id: int,
        **kwargs,
    ) -> Optional[DeviceProfile]:
        """Update device profile.

        Args:
            db: Database session.
            profile_id: Profile ID.
            **kwargs: Fields to update.

        Returns:
            Updated device profile if found, None otherwise.
        """
        profile = await DeviceProfileCRUD.get_by_id(db, profile_id)
        if profile:
            # If setting as default, unset other defaults
            if kwargs.get('is_default', False):
                await DeviceProfileCRUD.unset_default(db)

            for key, value in kwargs.items():
                if hasattr(profile, key):
                    if key.endswith('_config') and isinstance(value, dict):
                        setattr(profile, key, json.dumps(value))
                    else:
                        setattr(profile, key, value)
            await db.commit()
            await db.refresh(profile)
        return profile

    @staticmethod
    async def delete(db: AsyncSession, profile_id: int) -> bool:
        """Delete device profile.

        Args:
            db: Database session.
            profile_id: Profile ID.

        Returns:
            True if deleted, False if not found.
        """
        profile = await DeviceProfileCRUD.get_by_id(db, profile_id)
        if profile:
            await db.delete(profile)
            await db.commit()
            return True
        return False

    @staticmethod
    async def unset_default(db: AsyncSession) -> None:
        """Unset all default device profiles.

        Args:
            db: Database session.
        """
        result = await db.execute(select(DeviceProfile).where(DeviceProfile.is_default == True))
        profiles = result.scalars().all()
        for profile in profiles:
            profile.is_default = False
        await db.commit()


class DeviceSetupCRUD:
    """CRUD operations for DeviceSetup model."""

    @staticmethod
    async def create(
        db: AsyncSession,
        setup_type: str,
        device_name: str,
        profile_id: Optional[int] = None,
        port_path: Optional[str] = None,
        baud_rate: Optional[int] = None,
        status: str = "pending",
    ) -> DeviceSetup:
        """Create a new device setup.

        Args:
            db: Database session.
            setup_type: Type of setup (gps, obd, meshtastic).
            device_name: Name of the device.
            profile_id: Optional profile ID.
            port_path: Optional port path.
            baud_rate: Optional baud rate.
            status: Setup status.

        Returns:
            Created device setup.
        """
        setup = DeviceSetup(
            profile_id=profile_id,
            setup_type=setup_type,
            device_name=device_name,
            port_path=port_path,
            baud_rate=baud_rate,
            status=status,
        )
        db.add(setup)
        await db.commit()
        await db.refresh(setup)
        return setup

    @staticmethod
    async def get_by_id(db: AsyncSession, setup_id: int) -> Optional[DeviceSetup]:
        """Get device setup by ID.

        Args:
            db: Database session.
            setup_id: Setup ID.

        Returns:
            Device setup if found, None otherwise.
        """
        result = await db.execute(select(DeviceSetup).where(DeviceSetup.id == setup_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_profile(
        db: AsyncSession,
        profile_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DeviceSetup]:
        """Get device setups by profile ID.

        Args:
            db: Database session.
            profile_id: Profile ID.
            limit: Maximum number of setups to return.
            offset: Number of setups to skip.

        Returns:
            List of device setups.
        """
        result = await db.execute(
            select(DeviceSetup)
            .where(DeviceSetup.profile_id == profile_id)
            .order_by(DeviceSetup.created_utc.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_type(
        db: AsyncSession,
        setup_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DeviceSetup]:
        """Get device setups by type.

        Args:
            db: Database session.
            setup_type: Setup type.
            limit: Maximum number of setups to return.
            offset: Number of setups to skip.

        Returns:
            List of device setups.
        """
        result = await db.execute(
            select(DeviceSetup)
            .where(DeviceSetup.setup_type == setup_type)
            .order_by(DeviceSetup.created_utc.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession,
        setup_id: int,
        **kwargs,
    ) -> Optional[DeviceSetup]:
        """Update device setup.

        Args:
            db: Database session.
            setup_id: Setup ID.
            **kwargs: Fields to update.

        Returns:
            Updated device setup if found, None otherwise.
        """
        setup = await DeviceSetupCRUD.get_by_id(db, setup_id)
        if setup:
            for key, value in kwargs.items():
                if hasattr(setup, key):
                    setattr(setup, key, value)
            await db.commit()
            await db.refresh(setup)
        return setup

    @staticmethod
    async def delete(db: AsyncSession, setup_id: int) -> bool:
        """Delete device setup.

        Args:
            db: Database session.
            setup_id: Setup ID.

        Returns:
            True if deleted, False if not found.
        """
        setup = await DeviceSetupCRUD.get_by_id(db, setup_id)
        if setup:
            await db.delete(setup)
            await db.commit()
            return True
        return False


# Create CRUD instances
session_crud = SessionCRUD()
signal_crud = SignalCRUD()
frame_crud = FrameCRUD()
device_profile_crud = DeviceProfileCRUD()
device_setup_crud = DeviceSetupCRUD()