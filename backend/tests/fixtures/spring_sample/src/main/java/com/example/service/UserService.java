package com.example.service;

import com.example.persistence.UserMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class UserService {
    private final UserMapper userMapper;

    public UserDto findUser(Long id) {
        return userMapper.selectById(id);
    }

    public UserDto createUser(UserDto user) {
        userMapper.insert(user);
        return user;
    }
}
